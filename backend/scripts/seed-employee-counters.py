"""Backfill employee counters (AssignedAssets, PendingRequests, PendingSignatures,
UnreadNotificationCount) on USER#<id> METADATA records.

Run once after deploying the CounterProcessor changes to initialize counters
for existing data. After this, the stream processor keeps them in sync.

Usage:
    python scripts/seed-employee-counters.py
"""

import os
import sys
import boto3
from boto3.dynamodb.conditions import Key, Attr

sys.path.insert(0, "services/lambdas/layers/shared/python")
from utils.enums import (
    Asset_Status_Enum,
    Issue_Status_Enum,
    Software_Status_Enum,
)

TABLE_NAME = os.environ.get("ASSETS_TABLE", "gms-production-assets")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

ISSUE_TERMINAL = {
    Issue_Status_Enum.RESOLVED,
    Issue_Status_Enum.REPLACEMENT_APPROVED,
    Issue_Status_Enum.REPLACEMENT_REJECTED,
}
SOFTWARE_TERMINAL = {
    Software_Status_Enum.SOFTWARE_INSTALL_APPROVED,
    Software_Status_Enum.SOFTWARE_INSTALL_REJECTED,
}


def get_all_users():
    """Get all user records."""
    items = []
    kwargs = {
        "IndexName": "EntityTypeIndex",
        "KeyConditionExpression": Key("EntityType").eq("USER"),
        "ProjectionExpression": "PK, UserID, #r",
        "ExpressionAttributeNames": {"#r": "Role"},
    }
    while True:
        resp = table.query(**kwargs)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return items


def count_assigned_assets(employee_id):
    count = 0
    kwargs = {
        "IndexName": "EmployeeAssetIndex",
        "KeyConditionExpression": Key("EmployeeAssetIndexPK").eq(
            f"EMPLOYEE#{employee_id}"
        ),
        "FilterExpression": Attr("Status").eq(Asset_Status_Enum.ASSIGNED),
        "Select": "COUNT",
    }
    while True:
        resp = table.query(**kwargs)
        count += resp["Count"]
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return count


def count_pending_requests(employee_id):
    count = 0
    # Issues
    kwargs = {
        "IndexName": "IssueEntityIndex",
        "KeyConditionExpression": Key("IssueEntityType").eq("ISSUE"),
        "FilterExpression": Attr("ReportedBy").eq(employee_id),
        "ProjectionExpression": "#s",
        "ExpressionAttributeNames": {"#s": "Status"},
    }
    while True:
        resp = table.query(**kwargs)
        for item in resp.get("Items", []):
            if item.get("Status") not in ISSUE_TERMINAL:
                count += 1
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    # Software requests
    kwargs = {
        "IndexName": "SoftwareEntityIndex",
        "KeyConditionExpression": Key("SoftwareEntityType").eq("SOFTWARE_REQUEST"),
        "FilterExpression": Attr("RequestedBy").eq(employee_id),
        "ProjectionExpression": "#s",
        "ExpressionAttributeNames": {"#s": "Status"},
    }
    while True:
        resp = table.query(**kwargs)
        for item in resp.get("Items", []):
            if item.get("Status") not in SOFTWARE_TERMINAL:
                count += 1
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return count


def count_pending_signatures(employee_id):
    count = 0
    # Get all assets assigned to this employee
    asset_ids = []
    kwargs = {
        "IndexName": "EmployeeAssetIndex",
        "KeyConditionExpression": Key("EmployeeAssetIndexPK").eq(
            f"EMPLOYEE#{employee_id}"
        ),
        "ProjectionExpression": "PK",
    }
    while True:
        resp = table.query(**kwargs)
        for item in resp.get("Items", []):
            asset_ids.append(item["PK"].replace("ASSET#", ""))
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    for asset_id in asset_ids:
        # Pending handovers
        handover_resp = table.query(
            KeyConditionExpression=Key("PK").eq(f"ASSET#{asset_id}")
            & Key("SK").begins_with("HANDOVER#"),
            ProjectionExpression="EmployeeID, AcceptedAt",
        )
        for item in handover_resp.get("Items", []):
            if item.get("EmployeeID") == employee_id and not item.get("AcceptedAt"):
                count += 1
        # Pending returns
        return_resp = table.query(
            KeyConditionExpression=Key("PK").eq(f"ASSET#{asset_id}")
            & Key("SK").begins_with("RETURN#"),
            ProjectionExpression="UserSignatureS3Key",
        )
        for item in return_resp.get("Items", []):
            if not item.get("UserSignatureS3Key"):
                count += 1
    return count


def count_unread_notifications(user_id):
    count = 0
    kwargs = {
        "KeyConditionExpression": Key("PK").eq(f"USER#{user_id}")
        & Key("SK").begins_with("NOTIFICATION#"),
        "FilterExpression": Attr("IsRead").eq(False),
        "Select": "COUNT",
    }
    while True:
        resp = table.query(**kwargs)
        count += resp["Count"]
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return count


def main():
    users = get_all_users()
    print(f"Found {len(users)} users")

    for user in users:
        user_id = user["UserID"]
        role = user.get("Role", "")
        print(f"\nProcessing {user_id} (role={role})...")

        assigned = count_assigned_assets(user_id)
        pending_req = count_pending_requests(user_id)
        pending_sig = count_pending_signatures(user_id)
        unread = count_unread_notifications(user_id)

        print(
            f"  AssignedAssets={assigned}, PendingRequests={pending_req}, "
            f"PendingSignatures={pending_sig}, UnreadNotificationCount={unread}"
        )

        table.update_item(
            Key={"PK": f"USER#{user_id}", "SK": "METADATA"},
            UpdateExpression="SET #aa = :aa, #pr = :pr, #ps = :ps, #unc = :unc",
            ExpressionAttributeNames={
                "#aa": "AssignedAssets",
                "#pr": "PendingRequests",
                "#ps": "PendingSignatures",
                "#unc": "UnreadNotificationCount",
            },
            ExpressionAttributeValues={
                ":aa": assigned,
                ":pr": pending_req,
                ":ps": pending_sig,
                ":unc": unread,
            },
        )
        print(f"  ✓ Updated")

    print(f"\nDone. Updated {len(users)} user records.")


if __name__ == "__main__":
    main()
