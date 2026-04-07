import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Attr, Key
from pydantic import ValidationError

from utils import success, error, get_item
from utils.auth import get_caller_info
from utils.enums import User_Role_Enum
from utils.pagination import PaginationInput, PaginatedResponse
from utils.ddb_helper import paginated_query

from model import AssetItem, ListAssetsParams

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)


def _build_filter_expression(
    query_params: ListAssetsParams, use_status_index: bool = False
):
    """Build a combined FilterExpression from all provided filter params.

    When use_status_index=True, the status filter is applied via KeyConditionExpression
    on StatusIndex, so it's excluded from the FilterExpression.
    """
    filters = []

    # Only add status as FilterExpression when NOT using StatusIndex
    if query_params.status and not use_status_index:
        filters.append(Attr("Status").eq(query_params.status.value))
    if query_params.category:
        filters.append(Attr("Category").eq(query_params.category))
    if query_params.brand:
        filters.append(Attr("Brand").contains(query_params.brand))
    if query_params.model_name:
        filters.append(Attr("Model").contains(query_params.model_name))
    if query_params.date_from:
        filters.append(Attr("CreatedAt").gte(query_params.date_from))
    if query_params.date_to:
        # Append end-of-day to make the range inclusive
        filters.append(Attr("CreatedAt").lte(query_params.date_to + "T23:59:59Z"))

    if not filters:
        return None

    combined = filters[0]
    for f in filters[1:]:
        combined = combined & f
    return combined


def _map_asset_item(item: dict) -> AssetItem:
    """Map a DynamoDB item to an AssetItem response model."""
    return AssetItem(
        asset_id=item["PK"].replace("ASSET#", ""),
        brand=item.get("Brand"),
        model=item.get("Model"),
        serial_number=item.get("SerialNumber"),
        status=item.get("Status", ""),
        category=item.get("Category"),
        assignment_date=item.get("EmployeeAssetIndexSK", "").replace("ASSET#", "")
        or None,
        condition=item.get("Condition"),
        created_at=item.get("CreatedAt"),
    )


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id, groups = get_caller_info(event)
        is_admin = (
            User_Role_Enum.IT_ADMIN in groups or User_Role_Enum.MANAGEMENT in groups
        )

        params = event.get("queryStringParameters") or {}

        pagination = PaginationInput.from_query_params(params)

        try:
            query_params = ListAssetsParams(
                sort_order=params.get("sort_order", "desc"),
                status=params.get("status"),
                category=params.get("category"),
                brand=params.get("brand"),
                model_name=params.get("model_name"),
                date_from=params.get("date_from"),
                date_to=params.get("date_to"),
            )
        except ValidationError as e:
            return error(str(e), 400)

        scan_index_forward = query_params.sort_order == "asc"

        if is_admin:
            # When status filter is provided, use StatusIndex GSI (KeyCondition on status)
            # instead of EntityTypeIndex + FilterExpression. This scans only assets
            # with the requested status instead of ALL assets.
            if query_params.status:
                key_condition = Key("StatusIndexPK").eq(
                    f"STATUS#{query_params.status.value}"
                )
                index_name = "StatusIndex"
                filter_exp = _build_filter_expression(
                    query_params, use_status_index=True
                )
            else:
                key_condition = Key("EntityType").eq("ASSET")
                index_name = "EntityTypeIndex"
                filter_exp = _build_filter_expression(query_params)

            items, next_cursor = paginated_query(
                table,
                index_name,
                key_condition,
                filter_exp,
                cursor=pagination.cursor,
                scan_index_forward=scan_index_forward,
            )

            assets = [_map_asset_item(item) for item in items]
        else:
            key_condition = Key("EmployeeAssetIndexPK").eq(f"EMPLOYEE#{actor_id}")
            filter_exp = _build_filter_expression(query_params)

            items, next_cursor = paginated_query(
                table,
                "EmployeeAssetIndex",
                key_condition,
                filter_exp,
                cursor=pagination.cursor,
                scan_index_forward=scan_index_forward,
            )

            assets = []
            for item in items:
                asset_id = item["PK"].replace("ASSET#", "")
                asset_item = get_item(
                    table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"}
                )
                if not asset_item:
                    continue
                assets.append(_map_asset_item(asset_item))

        response = PaginatedResponse(
            items=[item.model_dump() for item in assets],
            count=len(assets),
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
