"""
Fix script: Reset assets stuck in ISSUE_REPORTED after their issue was REPLACEMENT_REJECTED.

When an issue's replacement was rejected, the asset status should have been set to IN_STOCK
and the employee linkage cleared. This script finds affected records and fixes them.

For each affected asset:
- Sets asset Status → IN_STOCK
- Updates StatusIndexPK → STATUS#IN_STOCK
- Removes EmployeeAssetIndexPK and EmployeeAssetIndexSK (unlinks from employee)

Usage:
    python scripts/fix-replacement-rejected-assets.py --table gms-dev-assets --region ap-southeast-1
    python scripts/fix-replacement-rejected-assets.py --table gms-dev-assets --region ap-southeast-1 --dry-run
"""

import argparse
import sys

import boto3

sys.path.insert(0, "services/lambdas/layers/shared/python")
from utils.enums import Asset_Status_Enum, Issue_Status_Enum


def fix_records(table_name: str, region: str, dry_run: bool) -> None:
    ddb_client = boto3.client("dynamodb", region_name=region)

    print(
        f"Scanning table '{table_name}' for ISSUE# records with Status=REPLACEMENT_REJECTED..."
    )

    # Step 1: Find all issue records with REPLACEMENT_REJECTED status
    paginator = ddb_client.get_paginator("scan")
    pages = paginator.paginate(
        TableName=table_name,
        FilterExpression="begins_with(SK, :prefix) AND #s = :status",
        ExpressionAttributeNames={"#s": "Status"},
        ExpressionAttributeValues={
            ":prefix": {"S": "ISSUE#"},
            ":status": {"S": Issue_Status_Enum.REPLACEMENT_REJECTED},
        },
    )

    affected_asset_ids = set()
    for page in pages:
        for item in page.get("Items", []):
            pk = item["PK"]["S"]  # ASSET#<AssetID>
            asset_id = pk.replace("ASSET#", "")
            affected_asset_ids.add(asset_id)

    print(f"Found {len(affected_asset_ids)} assets with REPLACEMENT_REJECTED issues.")

    # Step 2: For each asset, check if the asset status is still ISSUE_REPORTED
    count = 0
    for asset_id in sorted(affected_asset_ids):
        resp = ddb_client.get_item(
            TableName=table_name,
            Key={"PK": {"S": f"ASSET#{asset_id}"}, "SK": {"S": "METADATA"}},
        )
        asset_item = resp.get("Item")
        if not asset_item:
            print(f"  SKIP (asset not found) AssetID={asset_id}")
            continue

        current_status = asset_item.get("Status", {}).get("S", "")
        if current_status != Asset_Status_Enum.ISSUE_REPORTED:
            print(f"  SKIP (status={current_status}) AssetID={asset_id}")
            continue

        if dry_run:
            print(f"  [DRY RUN] AssetID={asset_id} → Status=IN_STOCK, unlink employee")
            count += 1
            continue

        # Update asset: set IN_STOCK, update StatusIndexPK, remove employee linkage
        try:
            ddb_client.update_item(
                TableName=table_name,
                Key={
                    "PK": {"S": f"ASSET#{asset_id}"},
                    "SK": {"S": "METADATA"},
                },
                UpdateExpression=(
                    "SET #status = :new_status, #sipk = :sipk " "REMOVE #eaipk, #eaisk"
                ),
                ConditionExpression="#status = :old_status",
                ExpressionAttributeNames={
                    "#status": "Status",
                    "#sipk": "StatusIndexPK",
                    "#eaipk": "EmployeeAssetIndexPK",
                    "#eaisk": "EmployeeAssetIndexSK",
                },
                ExpressionAttributeValues={
                    ":new_status": {"S": Asset_Status_Enum.IN_STOCK},
                    ":old_status": {"S": Asset_Status_Enum.ISSUE_REPORTED},
                    ":sipk": {"S": f"STATUS#{Asset_Status_Enum.IN_STOCK.value}"},
                },
            )
            print(f"  FIXED AssetID={asset_id} → Status=IN_STOCK, employee unlinked")
            count += 1
        except ddb_client.exceptions.ConditionalCheckFailedException:
            print(f"  SKIP (condition failed, status changed) AssetID={asset_id}")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Total fixed: {count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fix assets stuck in ISSUE_REPORTED after REPLACEMENT_REJECTED"
    )
    parser.add_argument("--table", required=True, help="DynamoDB table name")
    parser.add_argument("--region", required=True, help="AWS region")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing",
    )
    args = parser.parse_args()
    fix_records(args.table, args.region, args.dry_run)
