import os

import boto3
from aws_lambda_powertools import Logger, Tracer

from utils import error, get_item, success
from utils.auth import require_roles
from utils.enums import User_Role_Enum

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)

COUNTER_KEY = {"PK": "ENTITY_COUNTERS", "SK": "METADATA"}

COUNTER_FIELDS = [
    "AssetCount",
    "IssueCount",
    "ReturnCount",
    "DisposalCount",
    "AssignmentCount",
    "SoftwareRequestCount",
]


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        require_roles(event, [User_Role_Enum.IT_ADMIN, User_Role_Enum.MANAGEMENT])

        item = get_item(table, COUNTER_KEY)

        counters = {
            field: int(item.get(field, 0)) if item else 0 for field in COUNTER_FIELDS
        }

        return success(counters)

    except PermissionError as e:
        return error(str(e), 403)
    except Exception:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
