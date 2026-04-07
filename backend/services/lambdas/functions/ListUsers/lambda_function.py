import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key, Attr
from pydantic import ValidationError

from utils import success, error
from utils.auth import require_group
from utils.enums import User_Role_Enum
from utils.pagination import PaginationInput, PaginatedResponse
from utils.ddb_helper import paginated_query

from model import ListUsersParams, UserItem

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        require_group(event, User_Role_Enum.IT_ADMIN)

        params = event.get("queryStringParameters") or {}

        pagination = PaginationInput.from_query_params(params)

        try:
            query_params = ListUsersParams(
                role=params.get("role"),
                status=params.get("status"),
                name=params.get("name"),
                sort_order=params.get("sort_order", "desc"),
            )
        except ValidationError as e:
            return error(str(e), 400)

        role = query_params.role
        status = query_params.status
        name = query_params.name
        scan_index_forward = query_params.sort_order == "asc"

        key_condition = Key("EntityType").eq("USER")

        filter_exp = None
        if role:
            filter_exp = Attr("Role").eq(role)
        if status:
            status_filter = Attr("Status").eq(status)
            filter_exp = (filter_exp & status_filter) if filter_exp else status_filter
        if name:
            name_filter = Attr("Fullname").contains(name)
            filter_exp = (filter_exp & name_filter) if filter_exp else name_filter

        items, next_cursor = paginated_query(
            table,
            "EntityTypeIndex",
            key_condition,
            filter_exp,
            cursor=pagination.cursor,
            scan_index_forward=scan_index_forward,
        )

        user_items = [
            UserItem(
                user_id=item["UserID"],
                fullname=item["Fullname"],
                email=item["Email"],
                role=item["Role"],
                status=item["Status"],
                created_at=item["CreatedAt"],
            )
            for item in items
        ]

        response = PaginatedResponse(
            items=[item.model_dump() for item in user_items],
            count=len(user_items),
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
