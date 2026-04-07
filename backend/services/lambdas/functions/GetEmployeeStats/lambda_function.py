import os

import boto3
from aws_lambda_powertools import Logger, Tracer

from utils import error, success, get_item
from utils.auth import require_group
from utils.enums import User_Role_Enum

from model import EmployeeStatsResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id = require_group(event, User_Role_Enum.EMPLOYEE)

        # Single get_item on USER#<id> METADATA — counters maintained by CounterProcessor
        user_item = get_item(table, {"PK": f"USER#{actor_id}", "SK": "METADATA"})
        if not user_item:
            return error("User not found", 404)

        response = EmployeeStatsResponse(
            assigned_assets=int(user_item.get("AssignedAssets", 0)),
            my_pending_requests=int(user_item.get("PendingRequests", 0)),
            pending_signatures=int(user_item.get("PendingSignatures", 0)),
        )
        return success(response.model_dump())

    except PermissionError as e:
        return error(str(e), 403)
    except Exception:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
