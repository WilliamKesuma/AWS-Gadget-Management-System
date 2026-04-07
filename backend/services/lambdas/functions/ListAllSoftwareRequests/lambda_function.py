import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Attr, Key
from pydantic import ValidationError

from utils import success, error
from utils.auth import get_caller_info
from utils.enums import Software_Status_Enum, User_Role_Enum
from utils.pagination import PaginationInput, PaginatedResponse
from utils.ddb_helper import paginated_query
from utils.user_resolver import resolve_user_names, collect_user_ids

from model import ListAllSoftwareRequestsParams, AllSoftwareRequestListItem

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)

TERMINAL_SOFTWARE_STATUSES = {
    Software_Status_Enum.SOFTWARE_INSTALL_APPROVED.value,
    Software_Status_Enum.SOFTWARE_INSTALL_REJECTED.value,
}


def _matches_text_filter(item_value: str, filter_value: str) -> bool:
    """Case-insensitive substring match."""
    return filter_value.lower() in item_value.lower()


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id, groups = get_caller_info(event)

        is_it_admin = User_Role_Enum.IT_ADMIN in groups
        is_management = User_Role_Enum.MANAGEMENT in groups
        is_employee = User_Role_Enum.EMPLOYEE in groups

        if not is_it_admin and not is_management and not is_employee:
            raise PermissionError("Insufficient permissions")

        params = event.get("queryStringParameters") or {}

        pagination = PaginationInput.from_query_params(params)

        try:
            query_params = ListAllSoftwareRequestsParams(
                sort_order=params.get("sort_order", "desc"),
                status=params.get("status"),
                risk_level=params.get("risk_level"),
                software_name=params.get("software_name"),
                vendor=params.get("vendor"),
                history=params.get("history", "false").lower() == "true",
                asset_id=params.get("asset_id"),
            )
        except ValidationError as e:
            return error(str(e), 400)

        scan_index_forward = query_params.sort_order == "asc"

        # Query strategy based on status filter
        filter_exp = None

        if query_params.status:
            key_condition = Key("SoftwareStatusIndexPK").eq(
                f"SOFTWARE_STATUS#{query_params.status}"
            )
            index_name = "SoftwareStatusIndex"
        else:
            key_condition = Key("SoftwareEntityType").eq("SOFTWARE_REQUEST")
            index_name = "SoftwareEntityIndex"

        # Employee: filter to own requests only
        if is_employee and not is_it_admin and not is_management:
            filter_exp = Attr("RequestedBy").eq(actor_id)

        # Asset ID filter
        if query_params.asset_id:
            cond = Attr("PK").eq(f"ASSET#{query_params.asset_id}")
            filter_exp = (filter_exp & cond) if filter_exp else cond

        # History filter: exclude terminal statuses when history=false
        if not query_params.history and not query_params.status:
            for terminal_status in TERMINAL_SOFTWARE_STATUSES:
                cond = Attr("Status").ne(terminal_status)
                filter_exp = (filter_exp & cond) if filter_exp else cond

        # Additional filters
        if query_params.risk_level:
            cond = Attr("RiskLevel").eq(query_params.risk_level)
            filter_exp = (filter_exp & cond) if filter_exp else cond

        items, next_cursor = paginated_query(
            table,
            index_name,
            key_condition,
            filter_exp,
            cursor=pagination.cursor,
            scan_index_forward=scan_index_forward,
        )

        # Apply Python-side case-insensitive text filters
        if query_params.software_name:
            items = [
                i
                for i in items
                if _matches_text_filter(
                    i.get("SoftwareName", ""), query_params.software_name
                )
            ]
        if query_params.vendor:
            items = [
                i
                for i in items
                if _matches_text_filter(i.get("Vendor", ""), query_params.vendor)
            ]

        # Resolve user IDs to names
        all_user_ids: set[str] = set()
        for item in items:
            all_user_ids.update(
                collect_user_ids(
                    item["RequestedBy"],
                    item.get("ReviewedBy"),
                    item.get("ManagementReviewedBy"),
                )
            )
        names = resolve_user_names(table, all_user_ids)

        software_items = []
        for item in items:
            list_item = AllSoftwareRequestListItem(
                asset_id=item["PK"].replace("ASSET#", ""),
                software_request_id=item.get(
                    "SoftwareRequestID", item["SK"].replace("SOFTWARE#", "")
                ),
                software_name=item["SoftwareName"],
                version=item["Version"],
                vendor=item["Vendor"],
                justification=item["Justification"],
                license_type=item["LicenseType"],
                license_validity_period=item["LicenseValidityPeriod"],
                data_access_impact=item["DataAccessImpact"],
                status=item["Status"],
                risk_level=item.get("RiskLevel"),
                requested_by=names.get(item["RequestedBy"], item["RequestedBy"]),
                requested_by_id=item["RequestedBy"],
                reviewed_by=(
                    names.get(item["ReviewedBy"]) if item.get("ReviewedBy") else None
                ),
                reviewed_by_id=item.get("ReviewedBy"),
                rejection_reason=item.get("RejectionReason"),
                created_at=item["CreatedAt"],
                reviewed_at=item.get("ReviewedAt"),
                management_reviewed_by=(
                    names.get(item["ManagementReviewedBy"])
                    if item.get("ManagementReviewedBy")
                    else None
                ),
                management_reviewed_by_id=item.get("ManagementReviewedBy"),
                management_reviewed_at=item.get("ManagementReviewedAt"),
                management_rejection_reason=item.get("ManagementRejectionReason"),
                management_remarks=item.get("ManagementRemarks"),
            )
            software_items.append(list_item)

        response = PaginatedResponse(
            items=[item.model_dump() for item in software_items],
            count=len(software_items),
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
