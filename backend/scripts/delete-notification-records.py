"""
Delete all DynamoDB records where PK starts with 'USER#' and SK starts with 'NOTIFICATION#'.

This is a destructive operation. Use --dry-run first to preview what will be deleted.

Usage:
    python scripts/delete-notification-records.py --table gms-dev-assets --region ap-southeast-1 --dry-run
    python scripts/delete-notification-records.py --table gms-dev-assets --region ap-southeast-1
"""

import argparse

import boto3


def delete_notification_records(table_name: str, region: str, dry_run: bool) -> None:
    ddb_client = boto3.client("dynamodb", region_name=region)

    print(f"Scanning table '{table_name}' for NOTIFICATION records under USER# PKs...")

    paginator = ddb_client.get_paginator("scan")
    pages = paginator.paginate(
        TableName=table_name,
        ProjectionExpression="PK, SK",
        FilterExpression="begins_with(PK, :pk_prefix) AND begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={
            ":pk_prefix": {"S": "USER#"},
            ":sk_prefix": {"S": "NOTIFICATION#"},
        },
    )

    keys_to_delete = []
    for page in pages:
        for item in page.get("Items", []):
            keys_to_delete.append({"PK": item["PK"], "SK": item["SK"]})

    print(f"Found {len(keys_to_delete)} notification records to delete.")

    if not keys_to_delete:
        print("Nothing to delete.")
        return

    if dry_run:
        print("[DRY RUN] The following records would be deleted:")
        for key in keys_to_delete:
            print(f"  PK={key['PK']['S']}  SK={key['SK']['S']}")
        print(f"\n[DRY RUN] Total: {len(keys_to_delete)} records")
        return

    # Batch delete in chunks of 25 (DynamoDB limit)
    deleted = 0
    chunk_size = 25
    for i in range(0, len(keys_to_delete), chunk_size):
        chunk = keys_to_delete[i : i + chunk_size]
        request_items = {table_name: [{"DeleteRequest": {"Key": key}} for key in chunk]}

        response = ddb_client.batch_write_item(RequestItems=request_items)

        unprocessed = response.get("UnprocessedItems", {})
        while unprocessed:
            print(
                f"  Retrying {len(unprocessed.get(table_name, []))} unprocessed items..."
            )
            response = ddb_client.batch_write_item(RequestItems=unprocessed)
            unprocessed = response.get("UnprocessedItems", {})

        deleted += len(chunk)
        print(f"  Deleted {deleted}/{len(keys_to_delete)}...")

    print(f"\nDone. Total deleted: {deleted}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Delete all NOTIFICATION records stored under USER# PKs"
    )
    parser.add_argument("--table", required=True, help="DynamoDB table name")
    parser.add_argument("--region", required=True, help="AWS region")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deletions without writing",
    )
    args = parser.parse_args()
    delete_notification_records(args.table, args.region, args.dry_run)
