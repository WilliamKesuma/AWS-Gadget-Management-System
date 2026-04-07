import os
import uuid
from datetime import datetime, timezone

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key
from pydantic import ValidationError

from custom_exceptions import ConflictException
from utils import error, put_item, success
from utils.auth import require_group
from utils.enums import User_Role_Enum
from utils.models import AssetCategoryModel

from model import CreateAssetCategoryRequest, CreateAssetCategoryResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        require_group(event, User_Role_Enum.MANAGEMENT)

        body = json.loads(event.get("body") or "{}")
        request = CreateAssetCategoryRequest(**body)

        # Validate category_name is non-empty
        if not request.category_name or not request.category_name.strip():
            return error("category_name is required", 400)

        # Convert to SCREAMING_SNAKE_CASE
        formatted_name = request.category_name.strip().upper().replace(" ", "_")

        # Check for duplicate category name via GSI
        response = table.query(
            IndexName="CategoryNameIndex",
            KeyConditionExpression=Key("CategoryNameIndexPK").eq(
                f"CATEGORY_NAME#{formatted_name}"
            ),
            Limit=1,
        )
        if response.get("Count", 0) > 0:
            raise ConflictException(f"Category '{formatted_name}' already exists")

        # Generate UUID v4 and build record
        category_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        category = AssetCategoryModel(
            PK=f"CATEGORY#{category_id}",
            SK="METADATA",
            CategoryID=category_id,
            CategoryName=formatted_name,
            CreatedAt=now,
            CategoryEntityType="CATEGORY",
            CategoryNameIndexPK=f"CATEGORY_NAME#{formatted_name}",
        )

        put_item(table, category.model_dump(exclude_none=True))

        return success(
            CreateAssetCategoryResponse(
                category_id=category_id,
                category_name=formatted_name,
                created_at=now,
            ).model_dump(),
            status_code=201,
        )

    except ValidationError as e:
        return error(str(e), 400)
    except ValueError as e:
        return error(str(e), 400)
    except PermissionError as e:
        return error(str(e), 403)
    except ConflictException as e:
        return error(str(e), 409)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
