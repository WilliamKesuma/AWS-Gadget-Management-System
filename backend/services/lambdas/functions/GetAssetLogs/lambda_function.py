import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key
from pydantic import ValidationError

from custom_exceptions import NotFoundException
from utils import error, get_item, success
from utils.auth import require_roles
from utils.enums import User_Role_Enum
from utils.pagination import PaginationInput, PaginatedResponse
from utils.ddb_helper import paginated_query
from utils.user_resolver import collect_user_ids, resolve_user_names

from model import AuditLogItem

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        require_roles(event, [User_Role_Enum.IT_ADMIN, User_Role_Enum.MANAGEMENT])

        asset_id = event["pathParameters"]["asset_id"]

        params = event.get("queryStringParameters") or {}
        pagination = PaginationInput.from_query_params(params)

        # Verify asset exists
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        # Query all LOG# records for this asset (newest first)
        key_condition = Key("PK").eq(f"ASSET#{asset_id}") & Key("SK").begins_with(
            "LOG#"
        )

        items, next_cursor = paginated_query(
            table,
            None,
            key_condition,
            filter_exp=None,
            cursor=pagination.cursor,
            scan_index_forward=False,
        )

        # Batch-resolve actor names
        actor_ids = collect_user_ids(*[item["ActorID"] for item in items])
        names = resolve_user_names(table, actor_ids)

        log_items = []
        for item in items:
            # SK format: LOG#<timestamp>#<actor_id>
            sk_parts = item["SK"].split("#", 2)
            timestamp = sk_parts[1] if len(sk_parts) >= 2 else ""

            actor_id = item["ActorID"]
            log_items.append(
                AuditLogItem(
                    actor_id=actor_id,
                    actor_name=names.get(actor_id, actor_id),
                    phase=item["Phase"],
                    previous_status=item["PreviousStatus"],
                    new_status=item["NewStatus"],
                    rejection_reason=item.get("RejectionReason"),
                    remarks=item.get("Remarks"),
                    timestamp=timestamp,
                )
            )

        response = PaginatedResponse(
            items=[log.model_dump() for log in log_items],
            count=len(log_items),
            next_cursor=next_cursor,
            has_next_page=next_cursor is not None,
        )
        return success(response.model_dump())

    except PermissionError as e:
        return error(str(e), 403)
    except NotFoundException as e:
        return error(str(e), 404)
    except ValidationError as e:
        return error(str(e), 400)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
