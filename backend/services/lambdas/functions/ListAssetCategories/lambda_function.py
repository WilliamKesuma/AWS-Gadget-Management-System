import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key
from pydantic import ValidationError

from utils import success, error
from utils.auth import require_roles
from utils.enums import User_Role_Enum
from utils.pagination import PaginationInput, PaginatedResponse
from utils.ddb_helper import paginated_query

from model import CategoryItem

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        require_roles(event, [User_Role_Enum.MANAGEMENT, User_Role_Enum.IT_ADMIN])

        params = event.get("queryStringParameters") or {}

        pagination = PaginationInput.from_query_params(params)

        key_condition = Key("CategoryEntityType").eq("CATEGORY")

        items, next_cursor = paginated_query(
            table,
            "CategoryEntityIndex",
            key_condition,
            None,
            cursor=pagination.cursor,
        )

        category_items = [
            CategoryItem(
                category_id=item["CategoryID"],
                category_name=item["CategoryName"],
                created_at=item["CreatedAt"],
            )
            for item in items
        ]

        response = PaginatedResponse(
            items=[item.model_dump() for item in category_items],
            count=len(category_items),
            next_cursor=next_cursor,
            has_next_page=next_cursor is not None,
        )
        return success(response.model_dump())

    except ValidationError as e:
        return error(str(e), 400)
    except PermissionError as e:
        return error(str(e), 403)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
