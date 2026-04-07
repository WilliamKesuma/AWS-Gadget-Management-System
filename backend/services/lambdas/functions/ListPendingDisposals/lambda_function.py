import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Attr, Key
from pydantic import ValidationError

from utils import success, error, require_group
from utils.enums import Asset_Status_Enum, User_Role_Enum
from utils.pagination import PaginationInput, PaginatedResponse
from utils.ddb_helper import paginated_query
from utils.user_resolver import resolve_user_names, collect_user_ids
from model import AssetSpecs, ListPendingDisposalsParams, PendingDisposalItem

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)

DISPOSAL_STATUS_INDEX = "DisposalStatusIndex"
DISPOSAL_ENTITY_INDEX = "DisposalEntityIndex"

# Statuses to include when history=true (past management decisions)
HISTORY_DISPOSAL_STATUSES = {
    Asset_Status_Enum.DISPOSAL_PENDING.value,
    Asset_Status_Enum.DISPOSED.value,
    Asset_Status_Enum.DISPOSAL_REJECTED.value,
}


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        require_group(event, User_Role_Enum.MANAGEMENT)

        params = event.get("queryStringParameters") or {}

        pagination = PaginationInput.from_query_params(params)

        try:
            query_params = ListPendingDisposalsParams(
                sort_order=params.get("sort_order", "desc"),
                disposal_reason=params.get("disposal_reason"),
                history=params.get("history", "false").lower() == "true",
            )
        except ValidationError as e:
            return error(str(e), 400)

        scan_index_forward = query_params.sort_order == "asc"

        if query_params.history:
            # History mode: query all disposals, filter to relevant statuses
            key_condition = Key("DisposalEntityType").eq("DISPOSAL")
            index_name = DISPOSAL_ENTITY_INDEX

            filter_exp = (
                Attr("DisposalStatusIndexPK").eq(
                    f"DISPOSAL_STATUS#{Asset_Status_Enum.DISPOSAL_PENDING.value}"
                )
                | Attr("DisposalStatusIndexPK").eq(
                    f"DISPOSAL_STATUS#{Asset_Status_Enum.DISPOSED.value}"
                )
                | Attr("DisposalStatusIndexPK").eq(
                    f"DISPOSAL_STATUS#{Asset_Status_Enum.DISPOSAL_REJECTED.value}"
                )
            )
        else:
            # Default: only DISPOSAL_PENDING (needs action)
            key_condition = Key("DisposalStatusIndexPK").eq(
                f"DISPOSAL_STATUS#{Asset_Status_Enum.DISPOSAL_PENDING.value}"
            )
            index_name = DISPOSAL_STATUS_INDEX
            filter_exp = None

        if query_params.disposal_reason:
            cond = Attr("DisposalReason").eq(query_params.disposal_reason)
            filter_exp = (filter_exp & cond) if filter_exp else cond

        items, next_cursor = paginated_query(
            table,
            index_name,
            key_condition,
            filter_exp,
            cursor=pagination.cursor,
            scan_index_forward=scan_index_forward,
        )

        # Resolve user IDs to names
        all_user_ids: set[str] = set()
        for item in items:
            all_user_ids.update(
                collect_user_ids(
                    item["InitiatedBy"],
                    item.get("ManagementReviewedBy"),
                )
            )
        names = resolve_user_names(table, all_user_ids)

        disposals = []
        for item in items:
            asset_id = item["PK"].replace("ASSET#", "")
            disposal_id = item.get("DisposalID", item["SK"].replace("DISPOSAL#", ""))

            raw_status = item.get("DisposalStatusIndexPK") or ""
            disposal_status = raw_status.replace("DISPOSAL_STATUS#", "")

            asset_specs_data = item.get("AssetSpecs")
            asset_specs = None
            if asset_specs_data:
                asset_specs = AssetSpecs(
                    brand=asset_specs_data.get("Brand"),
                    model=asset_specs_data.get("Model"),
                    serial_number=asset_specs_data.get("SerialNumber"),
                    product_description=asset_specs_data.get("ProductDescription"),
                    cost=asset_specs_data.get("Cost"),
                    purchase_date=asset_specs_data.get("PurchaseDate"),
                )

            list_item = PendingDisposalItem(
                asset_id=asset_id,
                disposal_id=disposal_id,
                disposal_reason=item["DisposalReason"],
                justification=item["Justification"],
                asset_specs=asset_specs,
                initiated_by=names.get(item["InitiatedBy"], item["InitiatedBy"]),
                initiated_by_id=item["InitiatedBy"],
                initiated_at=item["InitiatedAt"],
                status=disposal_status,
                management_reviewed_by=(
                    names.get(item["ManagementReviewedBy"])
                    if item.get("ManagementReviewedBy")
                    else None
                ),
                management_reviewed_by_id=item.get("ManagementReviewedBy"),
                management_reviewed_at=item.get("ManagementReviewedAt"),
            )
            disposals.append(list_item)

        response = PaginatedResponse(
            items=[item.model_dump() for item in disposals],
            count=len(disposals),
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
