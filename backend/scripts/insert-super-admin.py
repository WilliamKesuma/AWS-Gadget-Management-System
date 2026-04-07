#!/usr/bin/env python3
"""Bootstrap script to create the first admin user directly via AWS Cognito + DynamoDB.

Usage:
    python scripts/insert-super-admin.py --email admin@example.com --password "MyPass@123" --role it_admin

NOTE: The PostConfirmation Cognito trigger does NOT fire for admin_create_user calls,
so this script writes the DynamoDB record directly.
"""

import argparse
import os
import sys
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

sys.path.insert(0, "services/lambdas/layers/shared/python")
from utils.enums import User_Role_Enum, User_Status_Enum

PROJECT = "gms"
REGION = "ap-southeast-1"

VALID_ROLES = {
    User_Role_Enum.IT_ADMIN,
    User_Role_Enum.MANAGEMENT,
    User_Role_Enum.EMPLOYEE,
    User_Role_Enum.FINANCE,
}

ROLE_TO_GROUP = {
    User_Role_Enum.IT_ADMIN: User_Role_Enum.IT_ADMIN,
    User_Role_Enum.MANAGEMENT: User_Role_Enum.MANAGEMENT,
    User_Role_Enum.EMPLOYEE: User_Role_Enum.EMPLOYEE,
    User_Role_Enum.FINANCE: User_Role_Enum.FINANCE,
}


def get_ssm(env: str, category: str, name: str) -> str:
    ssm = boto3.client("ssm", region_name=REGION)
    param = f"/{PROJECT}/{env}/{category}/{name}"
    try:
        return ssm.get_parameter(Name=param)["Parameter"]["Value"]
    except ClientError as e:
        print(f"Error fetching SSM param '{param}': {e}")
        sys.exit(1)


def create_admin_user(
    email: str, password: str, role: str, name: str, env: str
) -> None:
    role_enum = User_Role_Enum(role)
    user_pool_id = get_ssm(env, "auth", "user-pool-id")
    table_name = get_ssm(env, "storage", "assets-table-name")
    group_name = f"{PROJECT}-{env}-{ROLE_TO_GROUP[role_enum]}-group"

    cognito = boto3.client("cognito-idp", region_name=REGION)
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    # 1. Create Cognito user
    print(
        f"Creating Cognito user '{email}' (role: {role_enum}, pool: {user_pool_id})..."
    )
    try:
        response = cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=email,
            TemporaryPassword=password,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "name", "Value": name},
                {"Name": "custom:role", "Value": role_enum},
            ],
        )
        user_sub = next(
            a["Value"] for a in response["User"]["Attributes"] if a["Name"] == "sub"
        )
        print(f"  Created — sub: {user_sub}")
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "UsernameExistsException":
            print(f"  User '{email}' already exists.")
        else:
            print(f"  Failed to create user: {e}")
        sys.exit(1)

    # 2. Set permanent password (no forced change on first login)
    try:
        cognito.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=email,
            Password=password,
            Permanent=True,
        )
        print(f"  Password set as permanent.")
    except ClientError as e:
        print(f"  Failed to set permanent password: {e}")
        sys.exit(1)

    # 3. Add to Cognito group
    try:
        cognito.admin_add_user_to_group(
            UserPoolId=user_pool_id,
            Username=email,
            GroupName=role_enum,
        )
        print(f"  Added to group '{group_name}'.")
    except ClientError as e:
        print(f"  Failed to add user to group: {e}")
        sys.exit(1)

    # 4. Write DynamoDB record directly (PostConfirmation trigger does not fire for admin_create_user)
    now = datetime.now(timezone.utc).isoformat()
    try:
        table.put_item(
            Item={
                "PK": f"USER#{user_sub}",
                "SK": "METADATA",
                "UserID": user_sub,
                "Fullname": name,
                "Email": email,
                "Role": role_enum,
                "Status": User_Status_Enum.ACTIVE,
                "CreatedAt": now,
                "EntityType": "USER",
            }
        )
        print(f"  DynamoDB record created in '{table_name}'.")
    except ClientError as e:
        print(f"  Failed to write DynamoDB record: {e}")
        sys.exit(1)

    print(f"\nDone. '{email}' is ready to log in.")


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap a GMS user in Cognito + DynamoDB."
    )
    parser.add_argument(
        "--email", required=True, help="User email (used as Cognito username)"
    )
    parser.add_argument(
        "--password",
        required=True,
        help="Permanent password (no forced change on first login)",
    )
    parser.add_argument(
        "--role",
        required=True,
        choices=sorted(r.value for r in VALID_ROLES),
        help="User role",
    )
    parser.add_argument(
        "--name", default="", help="Full name (optional, defaults to email)"
    )
    parser.add_argument("--env", default="production")
    args = parser.parse_args()

    name = args.name or args.email
    create_admin_user(args.email, args.password, args.role, name, args.env)


if __name__ == "__main__":
    main()
