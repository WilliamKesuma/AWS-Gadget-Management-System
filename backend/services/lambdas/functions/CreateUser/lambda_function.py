import os
from datetime import datetime, timezone

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from pydantic import ValidationError

from custom_exceptions import ConflictException
from utils import success, error, put_item
from utils.auth import require_group
from utils.enums import User_Role_Enum, User_Status_Enum
from utils.models import UserMetadataModel

from model import CreateUserRequest, CreateUserResponse

logger = Logger()
tracer = Tracer()

USER_POOL_ID = os.environ["USER_POOL_ID"]
ASSETS_TABLE = os.environ["ASSETS_TABLE"]

cognito = boto3.client("cognito-idp")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        require_group(event, User_Role_Enum.IT_ADMIN)

        body = json.loads(event.get("body") or "{}")
        request = CreateUserRequest(**body)

        # Create user in Cognito with email as username and role as custom attribute
        cognito_response = cognito.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=request.email,
            TemporaryPassword=request.initial_password,
            UserAttributes=[
                {"Name": "email", "Value": request.email},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "name", "Value": request.fullname},
                {"Name": "custom:role", "Value": request.role},
            ],
        )

        # Extract sub from Cognito response
        user_sub = None
        for attr in cognito_response["User"]["Attributes"]:
            if attr["Name"] == "sub":
                user_sub = attr["Value"]
                break

        # Add user to the appropriate Cognito group
        cognito.admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=request.email,
            GroupName=request.role,
        )

        # Write DynamoDB record directly — PostConfirmation trigger does not fire
        # for admin_create_user since the user is created in FORCE_CHANGE_PASSWORD
        # state and never goes through a confirmation flow.
        now = datetime.now(timezone.utc).isoformat()
        user = UserMetadataModel(
            PK=f"USER#{user_sub}",
            SK="METADATA",
            UserID=user_sub,
            Fullname=request.fullname,
            Email=request.email,
            Role=request.role,
            Status=User_Status_Enum.ACTIVE,
            CreatedAt=now,
            EntityType="USER",
        )
        put_item(table, user.model_dump())

        response = CreateUserResponse(
            user_id=user_sub,
            role=request.role,
            status=User_Status_Enum.ACTIVE,
        )
        return success(response.model_dump(), status_code=201)

    except ValidationError as e:
        return error(str(e), 400)
    except PermissionError as e:
        return error(str(e), 403)
    except cognito.exceptions.UsernameExistsException:
        return error("User with this email already exists", 409)
    except ConflictException as e:
        return error(str(e), 409)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
