"""
Migration script: Add UUID ID fields to existing Return, Disposal, and Software Request records.

For each record type:
- ReturnRecordModel:          adds ReturnID = uuid4(), rewrites SK to RETURN#<uuid>
- DisposalRecordModel:        adds DisposalID = uuid4(), rewrites SK to DISPOSAL#<uuid>
- SoftwareInstallationModel:  adds SoftwareRequestID = uuid4(), rewrites SK to SOFTWARE#<uuid>

Because DynamoDB SKs are immutable, migration copies the item with the new SK and deletes the old one.
Records that already have a UUID-based SK (len == 36) are skipped.

Usage:
    python scripts/migrate-records-to-uuid.py --table gms-dev-assets --region ap-southeast-1
    python scripts/migrate-records-to-uuid.py --table gms-dev-assets --region ap-southeast-1 --dry-run
"""

import argparse
import uuid

import boto3
from boto3.dynamodb.types import TypeDeserializer

deserializer = TypeDeserializer()

UUID_LEN = 36  # len("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")


def is_uuid(value: str) -> bool:
    """Return True if value looks like a UUID v4 (36 chars, 4 hyphens)."""
    return len(value) == UUID_LEN and value.count("-") == 4


def deserialize_item(raw: dict) -> dict:
    return {k: deserializer.deserialize(v) for k, v in raw.items()}


def migrate_records(table_name: str, region: str, dry_run: bool) -> None:
    dynamodb = boto3.resource("dynamodb", region_name=region)
    ddb_client = boto3.client("dynamodb", region_name=region)
    table = dynamodb.Table(table_name)

    prefixes = [
        ("RETURN#", "ReturnID"),
        ("DISPOSAL#", "DisposalID"),
        ("SOFTWARE#", "SoftwareRequestID"),
    ]

    total_updated = 0

    paginator = ddb_client.get_paginator("scan")

    for sk_prefix, id_field in prefixes:
        print(f"\nMigrating {sk_prefix} records → rewriting SK to use UUID...")
        count = 0

        pages = paginator.paginate(
            TableName=table_name,
            FilterExpression="begins_with(SK, :prefix)",
            ExpressionAttributeValues={":prefix": {"S": sk_prefix}},
        )

        for page in pages:
            for raw_item in page.get("Items", []):
                pk = raw_item["PK"]["S"]
                old_sk = raw_item["SK"]["S"]

                # Extract the part after the prefix
                old_id_part = old_sk[len(sk_prefix) :]

                # Skip if SK already uses a UUID
                if is_uuid(old_id_part):
                    print(f"  SKIP (already UUID) PK={pk} SK={old_sk}")
                    continue

                # Determine the new UUID — reuse existing ID field if present, else generate
                existing_id = (
                    raw_item.get(id_field, {}).get("S")
                    if id_field in raw_item
                    else None
                )
                new_id = (
                    existing_id
                    if existing_id and is_uuid(existing_id)
                    else str(uuid.uuid4())
                )
                new_sk = f"{sk_prefix}{new_id}"

                if dry_run:
                    print(
                        f"  [DRY RUN] PK={pk}  {old_sk} → {new_sk}  ({id_field}={new_id})"
                    )
                    count += 1
                    continue

                # Deserialize full item
                item = deserialize_item(raw_item)

                # Build new item with updated SK and ID field
                new_item = {**item, "SK": new_sk, id_field: new_id}

                # Write new item then delete old one (transact to keep it atomic)
                ddb_client.transact_write_items(
                    TransactItems=[
                        {
                            "Put": {
                                "TableName": table_name,
                                "Item": {
                                    k: boto3.dynamodb.types.TypeSerializer().serialize(
                                        v
                                    )
                                    for k, v in new_item.items()
                                    if v is not None
                                },
                                "ConditionExpression": "attribute_not_exists(PK)",
                            }
                        },
                        {
                            "Delete": {
                                "TableName": table_name,
                                "Key": {
                                    "PK": {"S": pk},
                                    "SK": {"S": old_sk},
                                },
                            }
                        },
                    ]
                )

                print(f"  Migrated PK={pk}  {old_sk} → {new_sk}")
                count += 1

        print(
            f"  {count} records {'would be ' if dry_run else ''}migrated for {sk_prefix}"
        )
        total_updated += count

    print(
        f"\nDone. Total records {'to migrate' if dry_run else 'migrated'}: {total_updated}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate records to UUID-based SKs")
    parser.add_argument("--table", required=True, help="DynamoDB table name")
    parser.add_argument("--region", default="ap-southeast-1", help="AWS region")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without writing"
    )
    args = parser.parse_args()

    migrate_records(args.table, args.region, args.dry_run)
