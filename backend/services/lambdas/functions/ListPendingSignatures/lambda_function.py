import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key
from pydantic import ValidationError

from utils import success, error
from utils.auth import require_group
from utils.enums import User_Role_Enum
from utils.pagination import PaginationInput, PaginatedResponse
from utils.ddb_helper import paginated_query

from model import PendingSignatureItem

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)


def _get_pending_for_asset(
    asset_id: str, employee_id: str
) -> list[PendingSignatureItem]:
    """Fetch pending handover and return documents for a single asset."""
    pending = []

    response = table.query(
        KeyConditionExpression=Key("PK").eq(f"ASSET#{asset_id}")
        & Key("SK").begins_with("HANDOVER#"),
    )
    for item in response.get("Items", []):
        if item.get("EmployeeID") == employee_id and not item.get("AcceptedAt"):
            record_id = item.get("HandoverID", item["SK"].replace("HANDOVER#", ""))
            pending.append(
                PendingSignatureItem(
                    document_type="handover",
                    asset_id=asset_id,
                    record_id=record_id,
                    employee_name=item.get("EmployeeName"),
                    assignment_date=item.get("AssignmentDate"),
                    handover_form_s3_key=item.get("HandoverFormS3Key"),
                )
            )

    response = table.query(
        KeyConditionExpression=Key("PK").eq(f"ASSET#{asset_id}")
        & Key("SK").begins_with("RETURN#"),
    )
    for item in response.get("Items", []):
        if not item.get("UserSignatureS3Key"):
            record_id = item.get("ReturnID", item["SK"].replace("RETURN#", ""))
            pending.append(
                PendingSignatureItem(
                    document_type="return",
                    asset_id=asset_id,
                    record_id=record_id,
                    return_trigger=item.get("ReturnTrigger"),
                    initiated_at=item.get("InitiatedAt"),
                )
            )

    return pending


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id = require_group(event, User_Role_Enum.EMPLOYEE)

        params = event.get("queryStringParameters") or {}

        pagination = PaginationInput.from_query_params(params)

        # Cursor-based pagination over the employee's assigned assets
        key_condition = Key("EmployeeAssetIndexPK").eq(f"EMPLOYEE#{actor_id}")

        items, next_cursor = paginated_query(
            table,
            "EmployeeAssetIndex",
            key_condition,
            cursor=pagination.cursor,
            scan_index_forward=False,
        )

        # Secondary lookups only for the current page of assets — O(page_size)
        all_pending: list[PendingSignatureItem] = []
        for item in items:
            asset_id = item["PK"].replace("ASSET#", "")
            all_pending.extend(_get_pending_for_asset(asset_id, actor_id))

        response = PaginatedResponse(
            items=[item.model_dump() for item in all_pending],
            count=len(all_pending),
            next_cursor=next_cursor,
            has_next_page=next_cursor is not None,
        )
        return success(response.model_dump())

    except ValidationError as e:
        return error(str(e), 400)
    except PermissionError as e:
        return error(str(e), 403)
    except Exception:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
