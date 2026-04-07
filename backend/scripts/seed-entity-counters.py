#!/usr/bin/env python3
"""Seed the ENTITY_COUNTERS record by scanning existing DynamoDB data.

Usage:
    python scripts/seed-entity-counters.py [--env dev]

Scans the table once, counts assets (ASSET#/METADATA), issues (ISSUE#),
returns (RETURN#), disposals (DISPOSAL#), assignments (Status=ASSIGNED),
and software requests (SOFTWARE#), then writes a single counter record.

Safe to re-run — overwrites the counter record with fresh counts.
"""

import argparse
import sys

import boto3
from botocore.exceptions import ClientError

sys.path.insert(0, "services/lambdas/layers/shared/python")
from utils.enums import Asset_Status_Enum

PROJECT = "gms"
REGION = "ap-southeast-1"

COUNTER_KEY = {"PK": "ENTITY_COUNTERS", "SK": "METADATA"}


def get_ssm(env: str, category: str, name: str) -> str:
    ssm = boto3.client("ssm", region_name=REGION)
    param = f"/{PROJECT}/{env}/{category}/{name}"
    try:
        return ssm.get_parameter(Name=param)["Parameter"]["Value"]
    except ClientError as e:
        print(f"Error fetching SSM param '{param}': {e}")
        sys.exit(1)


def count_entities(table) -> dict:
    """Full table scan to count each entity type."""
    counters = {
        "AssetCount": 0,
        "IssueCount": 0,
        "ReturnCount": 0,
        "DisposalCount": 0,
        "AssignmentCount": 0,
        "SoftwareRequestCount": 0,
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

            # Asset metadata
            if pk.startswith("ASSET#") and sk == "METADATA":
                counters["AssetCount"] += 1
                if item.get("Status") == Asset_Status_Enum.ASSIGNED:
                    counters["AssignmentCount"] += 1

            # Sub-records
            elif sk.startswith("ISSUE#"):
                counters["IssueCount"] += 1
            elif sk.startswith("RETURN#"):
                counters["ReturnCount"] += 1
            elif sk.startswith("DISPOSAL#"):
                counters["DisposalCount"] += 1
            elif sk.startswith("SOFTWARE#"):
                counters["SoftwareRequestCount"] += 1

        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    print(f"Scanned {scanned} items total")
    return counters


def seed_counters(env: str) -> None:
    table_name = get_ssm(env, "storage", "assets-table-name")
    print(f"Table: {table_name}")

    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    counters = count_entities(table)

    item = {**COUNTER_KEY, **counters}
    table.put_item(Item=item)

    print("Entity counters seeded successfully:")
    for key, value in counters.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed entity counters")
    parser.add_argument("--env", default="dev", help="Environment (default: dev)")
    args = parser.parse_args()
    seed_counters(args.env)
