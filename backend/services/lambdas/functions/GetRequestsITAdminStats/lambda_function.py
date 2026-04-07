import os
from datetime import datetime, timezone

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Attr, Key

from utils import error, get_item, success
from utils.auth import require_roles
from utils.enums import Issue_Status_Enum, Software_Status_Enum, User_Role_Enum

from model import RequestsITAdminStatsResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)

DASHBOARD_KEY = {"PK": "DASHBOARD_COUNTERS", "SK": "METADATA"}

# Issue terminal statuses with their completion timestamp field
ISSUE_TERMINAL_STATUSES = {
    Issue_Status_Enum.RESOLVED.value: "ResolvedAt",
    Issue_Status_Enum.REPLACEMENT_APPROVED.value: "ManagementReviewedAt",
    Issue_Status_Enum.REPLACEMENT_REJECTED.value: "ManagementReviewedAt",
}

# Software terminal statuses with their completion timestamp field
SOFTWARE_TERMINAL_STATUSES = {
    Software_Status_Enum.SOFTWARE_INSTALL_APPROVED.value: "ReviewedAt",
    Software_Status_Enum.SOFTWARE_INSTALL_REJECTED.value: "ReviewedAt",
}


def _count_completed_today() -> int:
    """Count issues + software requests that reached terminal state today (UTC)."""
    today_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%dT")
    count = 0

    # Count terminal issues completed today
    for status, ts_field in ISSUE_TERMINAL_STATUSES.items():
        kwargs = {
            "IndexName": "IssueStatusIndex",
            "KeyConditionExpression": Key("IssueStatusIndexPK").eq(
                f"ISSUE_STATUS#{status}"
            ),
            "FilterExpression": Attr(ts_field).begins_with(today_prefix),
            "Select": "COUNT",
        }
        while True:
            response = table.query(**kwargs)
            count += response["Count"]
            if "LastEvaluatedKey" not in response:
                break
            kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    # Count terminal software requests completed today
    # SOFTWARE_INSTALL_APPROVED/REJECTED may have ManagementReviewedAt or ReviewedAt
    for status, ts_field in SOFTWARE_TERMINAL_STATUSES.items():
        # Try ReviewedAt first, then ManagementReviewedAt
        filter_exp = Attr(ts_field).begins_with(today_prefix) | Attr(
            "ManagementReviewedAt"
        ).begins_with(today_prefix)
        kwargs = {
            "IndexName": "SoftwareStatusIndex",
            "KeyConditionExpression": Key("SoftwareStatusIndexPK").eq(
                f"SOFTWARE_STATUS#{status}"
            ),
            "FilterExpression": filter_exp,
            "Select": "COUNT",
        }
        while True:
            response = table.query(**kwargs)
            count += response["Count"]
            if "LastEvaluatedKey" not in response:
                break
            kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    return count


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        require_roles(event, [User_Role_Enum.IT_ADMIN, User_Role_Enum.MANAGEMENT])

        # Pre-computed counters for total_active_requests and pending_returns
        item = get_item(table, DASHBOARD_KEY)
        total_active_requests = int(item.get("TotalActiveRequests", 0)) if item else 0
        pending_returns = int(item.get("PendingReturns", 0)) if item else 0

        # Live query for completed_today (resets daily)
        completed_today = _count_completed_today()

        response = RequestsITAdminStatsResponse(
            completed_today=completed_today,
            total_active_requests=total_active_requests,
            pending_returns=pending_returns,
        )
        return success(response.model_dump())

    except PermissionError as e:
        return error(str(e), 403)
    except Exception:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
