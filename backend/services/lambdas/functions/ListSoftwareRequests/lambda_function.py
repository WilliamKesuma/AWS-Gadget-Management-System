import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Attr, Key
from pydantic import ValidationError

from custom_exceptions import NotFoundException
from utils import success, error, get_item
from utils.enums import User_Role_Enum
from utils.pagination import PaginationInput, PaginatedResponse
from utils.ddb_helper import paginated_query
from utils.user_resolver import resolve_user_names, collect_user_ids

from model import ListSoftwareRequestsParams, SoftwareRequestListItem

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)


def _matches_text_filter(item_value: str, filter_value: str) -> bool:
    """Case-insensitive substring match."""
    return filter_value.lower() in item_value.lower()


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        # Extract caller claims and check authorization
        claims = event["requestContext"]["authorizer"]["claims"]
        groups = claims.get("cognito:groups", "").split(",")
        actor_id = claims["sub"]

        is_it_admin = User_Role_Enum.IT_ADMIN in groups
        is_employee = User_Role_Enum.EMPLOYEE in groups
        is_management = User_Role_Enum.MANAGEMENT in groups

        if not is_it_admin and not is_employee and not is_management:
            raise PermissionError("Insufficient permissions")

        asset_id = event["pathParameters"]["asset_id"]

        params = event.get("queryStringParameters") or {}

        pagination = PaginationInput.from_query_params(params)

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        # If employee, verify assignment via latest handover record
        if is_employee and not is_it_admin and not is_management:
            handover_response = table.query(
                KeyConditionExpression=Key("PK").eq(f"ASSET#{asset_id}")
                & Key("SK").begins_with("HANDOVER#"),
                ScanIndexForward=False,
                Limit=1,
            )
            handover_items = handover_response.get("Items", [])

            if not handover_items or handover_items[0].get("EmployeeID") != actor_id:
                raise PermissionError("You are not assigned to this asset")

        # Parse query params
        try:
            query_params = ListSoftwareRequestsParams(
                sort_order=params.get("sort_order", "desc"),
                status=params.get("status"),
                risk_level=params.get("risk_level"),
                software_name=params.get("software_name"),
                vendor=params.get("vendor"),
                license_validity_period=params.get("license_validity_period"),
                data_access_impact=params.get("data_access_impact"),
            )
        except ValidationError as e:
            return error(str(e), 400)

        scan_index_forward = query_params.sort_order == "asc"

        # Build server-side FilterExpression (exact matches only)
        filter_exp = None
        # Employees only see their own requests
        if is_employee and not is_it_admin and not is_management:
            filter_exp = Attr("RequestedBy").eq(actor_id)
        if query_params.status:
            cond = Attr("Status").eq(query_params.status)
            filter_exp = (filter_exp & cond) if filter_exp else cond
        if query_params.risk_level:
            cond = Attr("RiskLevel").eq(query_params.risk_level)
            filter_exp = (filter_exp & cond) if filter_exp else cond
        if query_params.data_access_impact:
            cond = Attr("DataAccessImpact").eq(query_params.data_access_impact)
            filter_exp = (filter_exp & cond) if filter_exp else cond

        key_condition = Key("PK").eq(f"ASSET#{asset_id}") & Key("SK").begins_with(
            "SOFTWARE#"
        )

        items, next_cursor = paginated_query(
            table,
            None,
            key_condition,
            filter_exp,
            cursor=pagination.cursor,
            scan_index_forward=scan_index_forward,
        )

        # Apply Python-side case-insensitive contains filters for text fields
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
        if query_params.license_validity_period:
            items = [
                i
                for i in items
                if _matches_text_filter(
                    i.get("LicenseValidityPeriod", ""),
                    query_params.license_validity_period,
                )
            ]

        # Resolve user IDs to names
        all_user_ids: set[str] = set()
        for item in items:
            all_user_ids.update(
                collect_user_ids(
                    item["RequestedBy"],
                    item.get("ReviewedBy"),
                )
            )
        names = resolve_user_names(table, all_user_ids)

        # Map each item to response model
        software_items = []
        for item in items:
            list_item = SoftwareRequestListItem(
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
    except NotFoundException as e:
        return error(str(e), 404)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
