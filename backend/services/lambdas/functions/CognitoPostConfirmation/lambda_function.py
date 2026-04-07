import os
from datetime import datetime, timezone

import boto3
from aws_lambda_powertools import Logger, Tracer

from utils import put_item
from utils.enums import User_Status_Enum
from utils.models import UserMetadataModel

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    """Cognito PostConfirmation trigger — syncs new user to DynamoDB.

    Fires after admin_create_user confirms a user. Reads user attributes
    from the trigger event and writes a UserMetadataModel record.
    """
    try:
        # userAttributes in Cognito triggers is a plain dict
        user_attrs = event["request"]["userAttributes"]

        user_sub = user_attrs["sub"]
        email = user_attrs.get("email", "")
        fullname = user_attrs.get("name", "")
        role = user_attrs.get("custom:role", "")

        now = datetime.now(timezone.utc).isoformat()

        user = UserMetadataModel(
            PK=f"USER#{user_sub}",
            SK="METADATA",
            UserID=user_sub,
            Fullname=fullname,
            Email=email,
            Role=role,
            Status=User_Status_Enum.ACTIVE,
            CreatedAt=now,
            EntityType="USER",
        )
        put_item(table, user.model_dump())

        logger.info("User record created", user_id=user_sub, email=email, role=role)

    except Exception:
        logger.exception("Failed to sync user to DynamoDB")
        # Re-raise so Cognito knows the trigger failed
        raise

    # Must return the event for Cognito triggers
    return event
