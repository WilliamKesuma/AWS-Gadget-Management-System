#!/usr/bin/env python3
"""Migration script: backfill IssueID (UUID) onto existing ISSUE# records.

Old records have:  SK = ISSUE#<timestamp>  and no IssueID field.
New records have:  SK = ISSUE#<uuid>       and IssueID = <uuid>.

This script:
  1. Scans all items whose SK begins with "ISSUE#"
  2. Skips any that already have an IssueID field (already migrated)
  3. For each old record:
     a. Generates a new UUID
     b. Writes a new item with SK = ISSUE#<uuid> and IssueID = <uuid>
     c. Updates IssueStatusIndexSK to ISSUE#<uuid> on the new item
     d. Deletes the old item
  4. Prints a summary

Usage:
    python scripts/migrate-issue-sk-to-uuid.py [--env dev] [--dry-run]
"""

import argparse
import os
import sys
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

PROJECT = "gms"
REGION = "ap-southeast-1"


def get_ssm(env: str, category: str, name: str) -> str:
    ssm = boto3.client("ssm", region_name=REGION)
    param = f"/{PROJECT}/{env}/{category}/{name}"
    try:
        return ssm.get_parameter(Name=param)["Parameter"]["Value"]
    except ClientError as e:
        print(f"[ERROR] Could not fetch SSM param '{param}': {e}")
        sys.exit(1)


def migrate(env: str, dry_run: bool) -> None:
    table_name = get_ssm(env, "storage", "assets-table-name")
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    print(f"Table : {table_name}")
    print(f"Mode  : {'DRY RUN — no writes' if dry_run else 'LIVE'}\n")

    migrated = 0
    skipped = 0
    errors = 0

    # Scan for all ISSUE# sort keys
    scan_kwargs = {
        "FilterExpression": Attr("SK").begins_with("ISSUE#"),
    }

    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])

        for item in items:
            sk = item["SK"]
            pk = item["PK"]
            raw_id = sk.replace("ISSUE#", "", 1)

            # Skip if already a UUID (36-char hyphenated format)
            if len(raw_id) == 36 and raw_id.count("-") == 4:
                skipped += 1
                continue

            # Also skip if IssueID field already present (partial previous run)
            if item.get("IssueID"):
                skipped += 1
                continue

            new_issue_id = str(uuid.uuid4())
            new_sk = f"ISSUE#{new_issue_id}"

            # Build the new item — copy everything, update SK and add IssueID
            new_item = {**item}
            new_item["SK"] = new_sk
            new_item["IssueID"] = new_issue_id

            # Update IssueStatusIndexSK to point to new SK
            if new_item.get("IssueStatusIndexSK"):
                new_item["IssueStatusIndexSK"] = new_sk

            print(f"  {pk}  |  {sk}  →  {new_sk}")

            if dry_run:
                migrated += 1
                continue

            try:
                # Write new item
                table.put_item(
                    Item=new_item,
                    ConditionExpression=Attr("SK").not_exists(),
                )
                # Delete old item
                table.delete_item(Key={"PK": pk, "SK": sk})
                migrated += 1
            except ClientError as e:
                code = e.response["Error"]["Code"]
                if code == "ConditionalCheckFailedException":
                    print(f"    [WARN] New SK already exists, skipping: {new_sk}")
                    skipped += 1
                else:
                    print(f"    [ERROR] {pk} / {sk}: {e}")
                    errors += 1

        # Paginate
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    print(f"\nDone.")
    print(f"  Migrated : {migrated}")
    print(f"  Skipped  : {skipped}")
    print(f"  Errors   : {errors}")

    if errors:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Migrate ISSUE# sort keys from timestamp to UUID."
    )
    parser.add_argument(
        "--env",
        default=os.environ.get("DEPLOY_ENV", "dev"),
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
