import os

import boto3
from aws_lambda_powertools import Logger, Tracer

from custom_exceptions import ConflictException, NotFoundException
from utils import success, error, get_item, update_item
from utils.auth import require_group
from utils.enums import User_Role_Enum, User_Status_Enum

from model import ReactivateUserResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]
USER_POOL_ID = os.environ["USER_POOL_ID"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
cognito = boto3.client("cognito-idp")


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        require_group(event, User_Role_Enum.IT_ADMIN)

        user_id = event["pathParameters"]["id"]

        # Fetch user record from DynamoDB
        item = get_item(table, {"PK": f"USER#{user_id}", "SK": "METADATA"})
        if not item:
            raise NotFoundException("User not found")

        if item["Status"] == User_Status_Enum.ACTIVE:
            raise ConflictException("User is already active")

        # Re-enable user in Cognito using email as username
        email = item["Email"]
        cognito.admin_enable_user(
            UserPoolId=USER_POOL_ID,
            Username=email,
        )

        # Update DynamoDB record status to active
        update_item(
            table,
            {"PK": f"USER#{user_id}", "SK": "METADATA"},
            {"Status": User_Status_Enum.ACTIVE},
        )

        response = ReactivateUserResponse(
            user_id=user_id,
            status=User_Status_Enum.ACTIVE,
            message="User reactivated successfully",
        )
        return success(response.model_dump())

    except PermissionError as e:
        return error(str(e), 403)
    except NotFoundException as e:
        return error(str(e), 404)
    except ConflictException as e:
        return error(str(e), 409)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
