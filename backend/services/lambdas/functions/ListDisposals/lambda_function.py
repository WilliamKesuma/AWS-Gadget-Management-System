import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Attr, Key
from pydantic import ValidationError

from utils import success, error
from utils.auth import get_caller_info
from utils.enums import Asset_Status_Enum, User_Role_Enum
from utils.pagination import PaginationInput, PaginatedResponse
from utils.ddb_helper import paginated_query
from utils.user_resolver import resolve_user_names, collect_user_ids

from model import DisposalListItem, ListDisposalsParams

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)

DISPOSAL_STATUS_INDEX = "DisposalStatusIndex"
DISPOSAL_ENTITY_INDEX = "DisposalEntityIndex"

IT_ADMIN_ACTIVE_STATUSES = {
    Asset_Status_Enum.DISPOSAL_REVIEW.value,
    Asset_Status_Enum.DISPOSAL_PENDING.value,
}
IT_ADMIN_HISTORY_STATUSES = {
    Asset_Status_Enum.DISPOSED.value,
    Asset_Status_Enum.DISPOSAL_REJECTED.value,
}
MANAGEMENT_ACTIVE_STATUSES = {Asset_Status_Enum.DISPOSAL_PENDING.value}
MANAGEMENT_HISTORY_STATUSES = {
    Asset_Status_Enum.DISPOSED.value,
    Asset_Status_Enum.DISPOSAL_REJECTED.value,
}


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id, groups = get_caller_info(event)

        is_it_admin = User_Role_Enum.IT_ADMIN in groups
        is_management = User_Role_Enum.MANAGEMENT in groups
        is_employee = User_Role_Enum.EMPLOYEE in groups

        if is_employee and not is_it_admin and not is_management:
            raise PermissionError("Employees cannot list global disposals")

        if not is_it_admin and not is_management:
            raise PermissionError("Insufficient permissions")

        params = event.get("queryStringParameters") or {}

        pagination = PaginationInput.from_query_params(params)

        status = params.get("status")

        try:
            query_params = ListDisposalsParams(
                sort_order=params.get("sort_order", "desc"),
                disposal_reason=params.get("disposal_reason"),
                date_from=params.get("date_from"),
                date_to=params.get("date_to"),
                history=params.get("history", "false").lower() == "true",
                asset_id=params.get("asset_id"),
            )
        except ValidationError as e:
            return error(str(e), 400)

        scan_index_forward = query_params.sort_order == "asc"

        # Determine which statuses to show based on role and history mode
        if is_it_admin:
            allowed_statuses = (
                IT_ADMIN_HISTORY_STATUSES
                if query_params.history
                else IT_ADMIN_ACTIVE_STATUSES
            )
        else:
            # management
            allowed_statuses = (
                MANAGEMENT_HISTORY_STATUSES
                if query_params.history
                else MANAGEMENT_ACTIVE_STATUSES
            )

        # If a specific status is requested, validate it's within the allowed set
        if status:
            if status not in allowed_statuses:
                return error(f"Status '{status}' is not accessible in this view", 403)
            key_condition = Key("DisposalStatusIndexPK").eq(f"DISPOSAL_STATUS#{status}")
            index_name = DISPOSAL_STATUS_INDEX
            filter_exp = None
        else:
            key_condition = Key("DisposalEntityType").eq("DISPOSAL")
            index_name = DISPOSAL_ENTITY_INDEX
            # Filter to only the allowed statuses for this role/mode
            status_conditions = [
                Attr("DisposalStatusIndexPK").eq(f"DISPOSAL_STATUS#{s}")
                for s in allowed_statuses
            ]
            filter_exp = status_conditions[0]
            for cond in status_conditions[1:]:
                filter_exp = filter_exp | cond

        if query_params.disposal_reason:
            cond = Attr("DisposalReason").eq(query_params.disposal_reason)
            filter_exp = (filter_exp & cond) if filter_exp else cond
        if query_params.date_from:
            cond = Attr("InitiatedAt").gte(query_params.date_from)
            filter_exp = (filter_exp & cond) if filter_exp else cond
        if query_params.date_to:
            cond = Attr("InitiatedAt").lte(query_params.date_to)
            filter_exp = (filter_exp & cond) if filter_exp else cond

        # Asset ID filter
        if query_params.asset_id:
            cond = Attr("PK").eq(f"ASSET#{query_params.asset_id}")
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
            if not disposal_status:
                logger.warning(
                    "Disposal record missing DisposalStatusIndexPK",
                    asset_id=asset_id,
                    disposal_id=disposal_id,
                )
                continue

            list_item = DisposalListItem(
                asset_id=asset_id,
                disposal_id=disposal_id,
                disposal_reason=item["DisposalReason"],
                justification=item["Justification"],
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
                management_rejection_reason=item.get("ManagementRejectionReason"),
                disposal_date=item.get("DisposalDate"),
                data_wipe_confirmed=item.get("DataWipeConfirmed"),
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
