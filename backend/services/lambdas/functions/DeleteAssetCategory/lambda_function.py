import os

import boto3
from aws_lambda_powertools import Logger, Tracer

from custom_exceptions import NotFoundException
from utils import delete_item, error, get_item, success
from utils.auth import require_group
from utils.enums import User_Role_Enum

from model import DeleteAssetCategoryResponse

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

        category_id = event["pathParameters"]["category_id"]

        key = {"PK": f"CATEGORY#{category_id}", "SK": "METADATA"}

        item = get_item(table, key)
        if not item:
            raise NotFoundException("Category not found")

        delete_item(table, key)

        return success(
            DeleteAssetCategoryResponse(
                category_id=category_id,
                message="Category deleted",
            ).model_dump(),
        )

    except PermissionError as e:
        return error(str(e), 403)
    except NotFoundException as e:
        return error(str(e), 404)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
