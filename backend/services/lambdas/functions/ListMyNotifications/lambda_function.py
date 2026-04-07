import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Attr, Key
from pydantic import ValidationError

from utils import success, error
from utils.auth import get_caller_info
from utils.pagination import PaginationInput, PaginatedResponse
from utils.ddb_helper import paginated_query

from model import ListMyNotificationsParams, NotificationListItem

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        caller_user_id, _groups = get_caller_info(event)

        params = event.get("queryStringParameters") or {}

        pagination = PaginationInput.from_query_params(params)

        # Parse optional is_read filter
        is_read_raw = params.get("is_read")
        is_read_value = None
        if is_read_raw is not None:
            if is_read_raw.lower() == "true":
                is_read_value = True
            elif is_read_raw.lower() == "false":
                is_read_value = False
            else:
                return error("is_read must be 'true' or 'false'", 400)

        try:
            query_params = ListMyNotificationsParams(
                sort_order=params.get("sort_order", "desc"),
                is_read=is_read_value,
            )
        except ValidationError as e:
            return error(str(e), 400)

        # Query main table: PK = USER#<caller_user_id>, SK begins_with NOTIFICATION#
        key_condition = Key("PK").eq(f"USER#{caller_user_id}") & Key("SK").begins_with(
            "NOTIFICATION#"
        )

        # Apply is_read filter if provided
        filter_exp = None
        if query_params.is_read is not None:
            filter_exp = Attr("IsRead").eq(query_params.is_read)

        scan_index_forward = query_params.sort_order == "asc"

        items, next_cursor = paginated_query(
            table,
            None,  # main table, no index
            key_condition,
            filter_exp,
            cursor=pagination.cursor,
            scan_index_forward=scan_index_forward,
        )

        # Get unread count from the user's metadata record (maintained by NotificationProcessor/MarkNotificationRead)
        user_item = table.get_item(
            Key={"PK": f"USER#{caller_user_id}", "SK": "METADATA"},
            ProjectionExpression="UnreadNotificationCount",
        ).get("Item", {})
        unread_count = int(user_item.get("UnreadNotificationCount", 0))
        # Guard against negative drift
        if unread_count < 0:
            unread_count = 0

        # Map items to NotificationListItem models
        notification_items = []
        for item in items:
            # SK = NOTIFICATION#<timestamp>#<uuid> → split by "#" and take the last part
            sk_parts = item["SK"].split("#")
            notification_id = sk_parts[-1]

            list_item = NotificationListItem(
                notification_id=notification_id,
                notification_type=item["NotificationType"],
                title=item["Title"],
                message=item["Message"],
                reference_id=item["ReferenceID"],
                reference_type=item["ReferenceType"],
                is_read=item["IsRead"],
                created_at=item["CreatedAt"],
            )
            notification_items.append(list_item)

        response = PaginatedResponse(
            items=[item.model_dump() for item in notification_items],
            count=len(notification_items),
            next_cursor=next_cursor,
            has_next_page=next_cursor is not None,
        )

        response_dict = response.model_dump()
        response_dict["unread_count"] = unread_count

        return success(response_dict)

    except ValidationError as e:
        return error(str(e), 400)
    except PermissionError as e:
        return error(str(e), 403)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
