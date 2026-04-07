import os
from datetime import datetime, timezone

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Attr, Key

from utils import error, success
from utils.auth import require_group
from utils.enums import Issue_Status_Enum, Software_Status_Enum, User_Role_Enum

from model import RequestsEmployeeStatsResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)

# Issue terminal statuses
ISSUE_TERMINAL = {
    Issue_Status_Enum.RESOLVED,
    Issue_Status_Enum.REPLACEMENT_APPROVED,
    Issue_Status_Enum.REPLACEMENT_REJECTED,
}

# Software terminal statuses
SOFTWARE_TERMINAL = {
    Software_Status_Enum.SOFTWARE_INSTALL_APPROVED,
    Software_Status_Enum.SOFTWARE_INSTALL_REJECTED,
}

# Resolved/approved terminal statuses (for resolved_monthly)
ISSUE_RESOLVED_STATUSES = {
    Issue_Status_Enum.RESOLVED,
    Issue_Status_Enum.REPLACEMENT_APPROVED,
}
SOFTWARE_RESOLVED_STATUSES = {Software_Status_Enum.SOFTWARE_INSTALL_APPROVED}


def _query_employee_issues(employee_id: str) -> list[dict]:
    """Fetch all issues reported by this employee (projected fields only)."""
    items = []
    kwargs = {
        "IndexName": "IssueEntityIndex",
        "KeyConditionExpression": Key("IssueEntityType").eq("ISSUE"),
        "FilterExpression": Attr("ReportedBy").eq(employee_id),
        "ProjectionExpression": "#s, ResolvedAt, ManagementReviewedAt",
        "ExpressionAttributeNames": {"#s": "Status"},
    }
    while True:
        response = table.query(**kwargs)
        items.extend(response.get("Items", []))
        if "LastEvaluatedKey" not in response:
            break
        kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
    return items


def _query_employee_software(employee_id: str) -> list[dict]:
    """Fetch all software requests by this employee (projected fields only)."""
    items = []
    kwargs = {
        "IndexName": "SoftwareEntityIndex",
        "KeyConditionExpression": Key("SoftwareEntityType").eq("SOFTWARE_REQUEST"),
        "FilterExpression": Attr("RequestedBy").eq(employee_id),
        "ProjectionExpression": "#s, ReviewedAt, ManagementReviewedAt",
        "ExpressionAttributeNames": {"#s": "Status"},
    }
    while True:
        response = table.query(**kwargs)
        items.extend(response.get("Items", []))
        if "LastEvaluatedKey" not in response:
            break
        kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
    return items


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id = require_group(event, User_Role_Enum.EMPLOYEE)

        month_prefix = datetime.now(timezone.utc).strftime("%Y-%m")

        issues = _query_employee_issues(actor_id)
        software = _query_employee_software(actor_id)

        active_requests = 0
        pending_approval = 0
        resolved_monthly = 0

        for item in issues:
            status = item.get("Status", "")
            if status not in ISSUE_TERMINAL:
                active_requests += 1
            if status == Issue_Status_Enum.TROUBLESHOOTING:
                pending_approval += 1
            # Resolved this month
            if status in ISSUE_RESOLVED_STATUSES:
                ts = item.get("ResolvedAt") or item.get("ManagementReviewedAt") or ""
                if ts.startswith(month_prefix):
                    resolved_monthly += 1

        for item in software:
            status = item.get("Status", "")
            if status not in SOFTWARE_TERMINAL:
                active_requests += 1
            if status == Software_Status_Enum.PENDING_REVIEW:
                pending_approval += 1
            # Resolved this month
            if status in SOFTWARE_RESOLVED_STATUSES:
                ts = item.get("ReviewedAt") or item.get("ManagementReviewedAt") or ""
                if ts.startswith(month_prefix):
                    resolved_monthly += 1

        response = RequestsEmployeeStatsResponse(
            active_requests=active_requests,
            pending_approval=pending_approval,
            resolved_monthly=resolved_monthly,
        )
        return success(response.model_dump())

    except PermissionError as e:
        return error(str(e), 403)
    except Exception:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
