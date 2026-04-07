#!/usr/bin/env python3
"""Seed the DASHBOARD_COUNTERS record by scanning existing DynamoDB data.

Usage:
    python scripts/seed-dashboard-counters.py [--env dev]

Scans the table once, computes all dashboard counter values from current data,
then writes a single DASHBOARD_COUNTERS record.

Safe to re-run — overwrites the counter record with fresh counts.
"""

import argparse
import sys
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

sys.path.insert(0, "services/lambdas/layers/shared/python")
from utils.enums import (
    Asset_Status_Enum,
    Issue_Status_Enum,
    Software_Status_Enum,
)

PROJECT = "gms"
REGION = "ap-southeast-1"

DASHBOARD_KEY = {"PK": "DASHBOARD_COUNTERS", "SK": "METADATA"}

# Asset statuses excluded from total active assets
EXCLUDED_ASSET_STATUSES = {
    Asset_Status_Enum.DISPOSED,
    Asset_Status_Enum.ASSET_PENDING_APPROVAL,
    Asset_Status_Enum.ASSET_REJECTED,
}

# Asset statuses that count as "in maintenance"
MAINTENANCE_STATUSES = {
    Asset_Status_Enum.UNDER_REPAIR,
    Asset_Status_Enum.ISSUE_REPORTED,
    Asset_Status_Enum.REPAIR_REQUIRED,
}

# Issue statuses actionable by IT Admin
PENDING_ISSUE_STATUSES = {
    Issue_Status_Enum.TROUBLESHOOTING,
    Issue_Status_Enum.UNDER_REPAIR,
    Issue_Status_Enum.SEND_WARRANTY,
}

# Issue terminal statuses
ISSUE_TERMINAL_STATUSES = {
    Issue_Status_Enum.RESOLVED,
    Issue_Status_Enum.REPLACEMENT_APPROVED,
    Issue_Status_Enum.REPLACEMENT_REJECTED,
}

# Software terminal statuses
SOFTWARE_TERMINAL_STATUSES = {
    Software_Status_Enum.SOFTWARE_INSTALL_APPROVED,
    Software_Status_Enum.SOFTWARE_INSTALL_REJECTED,
}


def get_ssm(env: str, category: str, name: str) -> str:
    ssm = boto3.client("ssm", region_name=REGION)
    param = f"/{PROJECT}/{env}/{category}/{name}"
    try:
        return ssm.get_parameter(Name=param)["Parameter"]["Value"]
    except ClientError as e:
        print(f"Error fetching SSM param '{param}': {e}")
        sys.exit(1)


def compute_dashboard_counters(table) -> dict:
    """Full table scan to compute all dashboard counter values."""
    counters = {
        "TotalActiveAssets": 0,
        "InMaintenance": 0,
        "PendingIssues": 0,
        "PendingApprovals": 0,
        "ScheduledDisposals": 0,
        "TotalDisposed": 0,
        "TotalAssetValue": 0,
        "InStock": 0,
        "Assigned": 0,
        "TotalActiveRequests": 0,
        "PendingReturns": 0,
        "CategoryCounts": {},
    }

    scan_kwargs = {}
    scanned = 0

    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])
        scanned += len(items)

        for item in items:
            pk = item.get("PK", "")
            sk = item.get("SK", "")

            # Asset metadata records
            if pk.startswith("ASSET#") and sk == "METADATA":
                status = item.get("Status", "")
                category = item.get("Category", "")
                cost = item.get("Cost")

                if status not in EXCLUDED_ASSET_STATUSES:
                    counters["TotalActiveAssets"] += 1

                    # Category distribution
                    if category:
                        counters["CategoryCounts"][category] = (
                            counters["CategoryCounts"].get(category, 0) + 1
                        )

                    # Asset value
                    if cost is not None:
                        counters["TotalAssetValue"] += int(cost)

                if status in MAINTENANCE_STATUSES:
                    counters["InMaintenance"] += 1

                if status == Asset_Status_Enum.IN_STOCK:
                    counters["InStock"] += 1

                if status == Asset_Status_Enum.ASSIGNED:
                    counters["Assigned"] += 1

                if status == Asset_Status_Enum.DISPOSED:
                    counters["TotalDisposed"] += 1

                # Management pending approvals from asset statuses
                if status == Asset_Status_Enum.ASSET_PENDING_APPROVAL:
                    counters["PendingApprovals"] += 1
                if status == Asset_Status_Enum.DISPOSAL_PENDING:
                    counters["PendingApprovals"] += 1
                    counters["ScheduledDisposals"] += 1

            # Issue records
            elif sk.startswith("ISSUE#"):
                status = item.get("Status", "")
                if status in PENDING_ISSUE_STATUSES:
                    counters["PendingIssues"] += 1
                if status == Issue_Status_Enum.REPLACEMENT_REQUIRED:
                    counters["PendingApprovals"] += 1
                # TotalActiveRequests — non-terminal issues
                if status not in ISSUE_TERMINAL_STATUSES:
                    counters["TotalActiveRequests"] += 1

            # Software request records
            elif sk.startswith("SOFTWARE#"):
                status = item.get("Status", "")
                if status == Software_Status_Enum.ESCALATED_TO_MANAGEMENT:
                    counters["PendingApprovals"] += 1
                # TotalActiveRequests — non-terminal software
                if status not in SOFTWARE_TERMINAL_STATUSES:
                    counters["TotalActiveRequests"] += 1

            # Return records
            elif sk.startswith("RETURN#"):
                resolved_status = item.get("ResolvedStatus")
                if not resolved_status:
                    counters["PendingReturns"] += 1

        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    print(f"Scanned {scanned} items total")
    return counters


def seed_dashboard_counters(env: str) -> None:
    table_name = get_ssm(env, "storage", "assets-table-name")
    print(f"Table: {table_name}")

    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    counters = compute_dashboard_counters(table)

    item = {**DASHBOARD_KEY, **counters}
    table.put_item(Item=item)

    print("\nDashboard counters seeded successfully:")
    for key, value in counters.items():
        if key == "CategoryCounts":
            print(f"  {key}:")
            for cat, cnt in sorted(value.items(), key=lambda x: x[1], reverse=True):
                print(f"    {cat}: {cnt}")
        else:
            print(f"  {key}: {value}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed dashboard counters")
    parser.add_argument("--env", default="dev", help="Environment (default: dev)")
    args = parser.parse_args()
    seed_dashboard_counters(args.env)
