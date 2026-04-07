"""
Migration script: Update Issue records with Status=ISSUE_REPORTED to TROUBLESHOOTING.

ISSUE_REPORTED was incorrectly used as the initial Issue record status. The correct
initial status is TROUBLESHOOTING. ISSUE_REPORTED belongs to Asset_Status_Enum only.

This script:
- Scans all ISSUE# records with Status = "ISSUE_REPORTED"
- Updates Status → "TROUBLESHOOTING"
- Updates IssueStatusIndexPK → "ISSUE_STATUS#TROUBLESHOOTING" (GSI key)

Usage:
    python scripts/migrate-issue-status-to-troubleshooting.py --table gms-dev-assets --region ap-southeast-1
    python scripts/migrate-issue-status-to-troubleshooting.py --table gms-dev-assets --region ap-southeast-1 --dry-run
"""

import argparse
import sys

import boto3

sys.path.insert(0, "services/lambdas/layers/shared/python")
from utils.enums import Asset_Status_Enum, Issue_Status_Enum


def migrate(table_name: str, region: str, dry_run: bool) -> None:
    ddb_client = boto3.client("dynamodb", region_name=region)

    print(
        f"Scanning table '{table_name}' for ISSUE# records with Status=ISSUE_REPORTED..."
    )

    paginator = ddb_client.get_paginator("scan")
    pages = paginator.paginate(
        TableName=table_name,
        FilterExpression="begins_with(SK, :prefix) AND #s = :old_status",
        ExpressionAttributeNames={"#s": "Status"},
        ExpressionAttributeValues={
            ":prefix": {"S": "ISSUE#"},
            ":old_status": {"S": Asset_Status_Enum.ISSUE_REPORTED},
        },
    )

    count = 0
    for page in pages:
        for item in page.get("Items", []):
            pk = item["PK"]["S"]
            sk = item["SK"]["S"]
            issue_id = item.get("IssueID", {}).get("S", sk.replace("ISSUE#", ""))

            if dry_run:
                print(f"  [DRY RUN] PK={pk} SK={sk} → Status=TROUBLESHOOTING")
                count += 1
                continue

            ddb_client.update_item(
                TableName=table_name,
                Key={"PK": {"S": pk}, "SK": {"S": sk}},
                UpdateExpression="SET #s = :new_status, IssueStatusIndexPK = :isipk",
                ConditionExpression="#s = :old_status",
                ExpressionAttributeNames={"#s": "Status"},
                ExpressionAttributeValues={
                    ":new_status": {"S": Issue_Status_Enum.TROUBLESHOOTING},
                    ":old_status": {"S": Asset_Status_Enum.ISSUE_REPORTED},
                    ":isipk": {
                        "S": f"ISSUE_STATUS#{Issue_Status_Enum.TROUBLESHOOTING.value}"
                    },
                },
            )
            print(f"  Migrated PK={pk} SK={sk} (IssueID={issue_id})")
            count += 1

    print(f"\nDone. {count} records {'would be ' if dry_run else ''}migrated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate Issue records from ISSUE_REPORTED to TROUBLESHOOTING status"
    )
    parser.add_argument("--table", required=True, help="DynamoDB table name")
    parser.add_argument("--region", default="ap-southeast-1", help="AWS region")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without writing"
    )
    args = parser.parse_args()

    migrate(args.table, args.region, args.dry_run)
