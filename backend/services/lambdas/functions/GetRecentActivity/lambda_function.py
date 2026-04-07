import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key

from utils import error, success
from utils.auth import require_roles
from utils.enums import User_Role_Enum

from model import RecentActivityItem, RecentActivityResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)

MAX_ITEMS = 5


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        require_roles(event, [User_Role_Enum.IT_ADMIN, User_Role_Enum.MANAGEMENT])

        # Query ActivityEntityIndex, newest first, limit 5
        response = table.query(
            IndexName="ActivityEntityIndex",
            KeyConditionExpression=Key("ActivityEntityType").eq("ACTIVITY"),
            ScanIndexForward=False,
            Limit=MAX_ITEMS,
        )

        items = []
        for item in response.get("Items", []):
            items.append(
                RecentActivityItem(
                    activity_id=item["ActivityID"],
                    activity=item["Activity"],
                    activity_type=item["ActivityType"],
                    actor_name=item["ActorName"],
                    actor_role=item["ActorRole"],
                    target_id=item["TargetID"],
                    target_type=item["TargetType"],
                    timestamp=item["Timestamp"],
                )
            )

        return success(RecentActivityResponse(items=items).model_dump())

    except PermissionError as e:
        return error(str(e), 403)
    except Exception:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
