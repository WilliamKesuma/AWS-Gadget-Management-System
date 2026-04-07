#!/usr/bin/env python3
"""Seed the four default asset categories into DynamoDB.

Usage:
    python scripts/seed-default-categories.py [--env dev]

Uses deterministic UUIDs (uuid5 with a fixed namespace) so each category
always gets the same CategoryID.  Combined with
ConditionExpression="attribute_not_exists(PK)", re-running the script is
safe — existing categories are silently skipped.
"""

import argparse
import os
import sys
import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

PROJECT = "gms"
REGION = "ap-southeast-1"

# Fixed namespace for deterministic category IDs
CATEGORY_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

DEFAULT_CATEGORIES = ["LAPTOP", "MOBILE_PHONE", "TABLET", "OTHERS"]


def get_ssm(env: str, category: str, name: str) -> str:
    ssm = boto3.client("ssm", region_name=REGION)
    param = f"/{PROJECT}/{env}/{category}/{name}"
    try:
        return ssm.get_parameter(Name=param)["Parameter"]["Value"]
    except ClientError as e:
        print(f"Error fetching SSM param '{param}': {e}")
        sys.exit(1)


def seed_default_categories(env: str) -> None:
    table_name = get_ssm(env, "storage", "assets-table-name")

    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    now = datetime.now(timezone.utc).isoformat()

    for category_name in DEFAULT_CATEGORIES:
        category_id = str(uuid.uuid5(CATEGORY_NAMESPACE, category_name))
        item = {
            "PK": f"CATEGORY#{category_id}",
            "SK": "METADATA",
            "CategoryID": category_id,
            "CategoryName": category_name,
            "CreatedAt": now,
            "CategoryEntityType": "CATEGORY",
            "CategoryNameIndexPK": f"CATEGORY_NAME#{category_name}",
        }

        try:
            table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(PK)",
            )
            print(f"  Created category: {category_name} (ID: {category_id})")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                print(f"  Skipped category: {category_name} (already exists)")
            else:
                print(f"  Failed to seed category '{category_name}': {e}")
                sys.exit(1)

    print(f"\nDone. Default categories seeded in '{table_name}'.")


def main():
    parser = argparse.ArgumentParser(
        description="Seed default asset categories into DynamoDB."
    )
    parser.add_argument(
        "--env",
        default=os.environ.get("DEPLOY_ENV", "dev"),
        help="Environment (default: dev)",
    )
    args = parser.parse_args()

    print(f"Seeding default categories for env '{args.env}'...")
    seed_default_categories(args.env)


if __name__ == "__main__":
    main()
