import os

import boto3
from aws_lambda_powertools import Logger, Tracer

from utils import error, get_item, success
from utils.auth import require_group
from utils.enums import User_Role_Enum

from model import ITAdminStatsResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)

DASHBOARD_KEY = {"PK": "DASHBOARD_COUNTERS", "SK": "METADATA"}


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        require_group(event, User_Role_Enum.IT_ADMIN)

        item = get_item(table, DASHBOARD_KEY)

        response = ITAdminStatsResponse(
            total_assets=int(item.get("TotalActiveAssets", 0)) if item else 0,
            pending_issues=int(item.get("PendingIssues", 0)) if item else 0,
            in_maintenance=int(item.get("InMaintenance", 0)) if item else 0,
        )
        return success(response.model_dump())

    except PermissionError as e:
        return error(str(e), 403)
    except Exception:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
