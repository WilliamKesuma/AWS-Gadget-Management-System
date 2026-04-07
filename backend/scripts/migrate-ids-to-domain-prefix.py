#!/usr/bin/env python3
"""Migrate existing UUID-based IDs to domain-prefixed format.

Rewrites IDs for Issue, Disposal, Return, and Software Request records from
UUID format (e.g. "a1b2c3d4-...") to domain-prefixed format
(e.g. "ISSUE-202605-1").

For each record:
  1. Reads the existing CreatedAt/InitiatedAt timestamp to derive YYYYMM
  2. Atomically increments a DOMAIN_COUNTER#{domain}#{YYYYMM} counter
  3. Builds the new ID: {DOMAIN}-{YYYYMM}-{count}
  4. Copies the item with updated SK, ID field, and GSI keys
  5. Deletes the old item

Because DynamoDB SKs are immutable, migration copies + deletes atomically.
Records that already have a domain-prefixed ID are skipped.

Usage:
    python scripts/migrate-ids-to-domain-prefix.py [--env dev]
    python scripts/migrate-ids-to-domain-prefix.py [--env dev] --dry-run
"""

import argparse
import re
import sys
from collections import defaultdict

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

PROJECT = "gms"
REGION = "ap-southeast-1"

# Pattern: DOMAIN-YYYYMM-N (already migrated)
DOMAIN_ID_PATTERN = re.compile(r"^[A-Z]+-\d{6}-\d+$")

DOMAIN_CONFIG = [
    {
        "sk_prefix": "ISSUE#",
        "id_field": "IssueID",
        "domain": "ISSUE",
        "timestamp_field": "CreatedAt",
        "gsi_sk_field": "IssueStatusIndexSK",
    },
    {
        "sk_prefix": "DISPOSAL#",
        "id_field": "DisposalID",
        "domain": "DISPOSAL",
        "timestamp_field": "InitiatedAt",
        "gsi_sk_field": "DisposalStatusIndexSK",
    },
    {
        "sk_prefix": "RETURN#",
        "id_field": "ReturnID",
        "domain": "RETURN",
        "timestamp_field": "InitiatedAt",
        "gsi_sk_field": None,
    },
    {
        "sk_prefix": "SOFTWARE#",
        "id_field": "SoftwareRequestID",
        "domain": "SOFTWARE",
        "timestamp_field": "CreatedAt",
        "gsi_sk_field": "SoftwareStatusIndexSK",
    },
]


def get_ssm(env: str, category: str, name: str) -> str:
    ssm = boto3.client("ssm", region_name=REGION)
    param = f"/{PROJECT}/{env}/{category}/{name}"
    try:
        return ssm.get_parameter(Name=param)["Parameter"]["Value"]
    except ClientError as e:
        print(f"[ERROR] Could not fetch SSM param '{param}': {e}")
        sys.exit(1)


def extract_year_month(timestamp: str) -> str:
    """Extract YYYYMM from an ISO-8601 timestamp like '2025-06-15T10:30:00+00:00'."""
    return timestamp[:7].replace("-", "")


def is_already_migrated(id_value: str) -> bool:
    """Check if the ID already uses domain-prefixed format."""
    return bool(DOMAIN_ID_PATTERN.match(id_value))


def increment_domain_counter(table, domain: str, year_month: str) -> int:
    """Atomically increment and return the counter for a domain+month."""
    response = table.update_item(
        Key={"PK": f"DOMAIN_COUNTER#{domain}#{year_month}", "SK": "METADATA"},
        UpdateExpression="ADD #count :inc",
        ExpressionAttributeNames={"#count": "Count"},
        ExpressionAttributeValues={":inc": 1},
        ReturnValues="UPDATED_NEW",
    )
    return int(response["Attributes"]["Count"])


def migrate(env: str, dry_run: bool) -> None:
    table_name = get_ssm(env, "storage", "assets-table-name")
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    print(f"Table : {table_name}")
    print(f"Mode  : {'DRY RUN — no writes' if dry_run else 'LIVE'}\n")

    # Phase 1: Scan and group records by domain + year_month for sequential numbering
    for config in DOMAIN_CONFIG:
        sk_prefix = config["sk_prefix"]
        id_field = config["id_field"]
        domain = config["domain"]
        ts_field = config["timestamp_field"]
        gsi_sk_field = config["gsi_sk_field"]

        print(f"--- Migrating {domain} records ---")

        # Collect all records that need migration, grouped by year_month
        records_by_month: dict[str, list[dict]] = defaultdict(list)
        skipped = 0

        scan_kwargs = {
            "FilterExpression": Attr("SK").begins_with(sk_prefix),
        }

        while True:
            response = table.scan(**scan_kwargs)
            for item in response.get("Items", []):
                old_id = item.get(id_field, "")

                # Skip if already migrated
                if is_already_migrated(old_id):
                    skipped += 1
                    continue

                timestamp = item.get(ts_field, "")
                if not timestamp or len(timestamp) < 7:
                    print(
                        f"  [WARN] Missing {ts_field} on PK={item['PK']} SK={item['SK']}, skipping"
                    )
                    skipped += 1
                    continue

                year_month = extract_year_month(timestamp)
                records_by_month[year_month].append(item)

            if "LastEvaluatedKey" not in response:
                break
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

        # Phase 2: Sort each month's records by timestamp and migrate sequentially
        migrated = 0
        errors = 0

        for year_month in sorted(records_by_month.keys()):
            items = records_by_month[year_month]
            # Sort by timestamp for deterministic ordering
            items.sort(key=lambda x: x.get(ts_field, ""))

            for item in items:
                pk = item["PK"]
                old_sk = item["SK"]

                if dry_run:
                    new_id = f"{domain}-{year_month}-{migrated + 1}"
                    print(
                        f"  [DRY RUN] PK={pk}  {old_sk} → {sk_prefix}{new_id}  ({id_field}={new_id})"
                    )
                    migrated += 1
                    continue

                try:
                    count = increment_domain_counter(table, domain, year_month)
                    new_id = f"{domain}-{year_month}-{count}"
                    new_sk = f"{sk_prefix}{new_id}"

                    # Build new item
                    new_item = {**item}
                    new_item["SK"] = new_sk
                    new_item[id_field] = new_id

                    # Update GSI SK field if applicable
                    if gsi_sk_field and gsi_sk_field in new_item:
                        new_item[gsi_sk_field] = f"{sk_prefix}{new_id}"

                    # Atomic: put new + delete old
                    table.put_item(
                        Item=new_item,
                        ConditionExpression=Attr("SK").not_exists(),
                    )
                    table.delete_item(Key={"PK": pk, "SK": old_sk})

                    print(f"  Migrated PK={pk}  {old_sk} → {new_sk}")
                    migrated += 1

                except ClientError as e:
                    code = e.response["Error"]["Code"]
                    if code == "ConditionalCheckFailedException":
                        print(
                            f"  [WARN] New SK already exists, skipping: {pk} {new_sk}"
                        )
                        skipped += 1
                    else:
                        print(f"  [ERROR] {pk} / {old_sk}: {e}")
                        errors += 1

        print(f"  Migrated: {migrated}  Skipped: {skipped}  Errors: {errors}\n")

    print("Done.")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate entity IDs from UUID to domain-prefixed format."
    )
    parser.add_argument(
        "--env",
        default="dev",
        help="Environment name (default: dev)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be migrated without making any changes",
    )
    args = parser.parse_args()
    migrate(args.env, args.dry_run)


if __name__ == "__main__":
    main()
