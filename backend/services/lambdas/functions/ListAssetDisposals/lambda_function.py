import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Attr, Key
from pydantic import ValidationError

from utils import success, error
from utils.auth import get_caller_info
from utils.enums import User_Role_Enum
from utils.pagination import PaginationInput, PaginatedResponse
from utils.ddb_helper import paginated_query
from utils.user_resolver import resolve_user_names, collect_user_ids

from model import ListAssetDisposalsParams, AssetDisposalListItem

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id, groups = get_caller_info(event)

        is_it_admin = User_Role_Enum.IT_ADMIN in groups
        is_management = User_Role_Enum.MANAGEMENT in groups
        is_employee = User_Role_Enum.EMPLOYEE in groups

        if is_employee and not is_it_admin and not is_management:
            raise PermissionError("Employees cannot list disposals")

        if not is_it_admin and not is_management:
            raise PermissionError("Insufficient permissions")

        asset_id = event["pathParameters"]["asset_id"]

        params = event.get("queryStringParameters") or {}

        pagination = PaginationInput.from_query_params(params)

        try:
            query_params = ListAssetDisposalsParams(
                sort_order=params.get("sort_order", "desc"),
                status=params.get("status"),
            )
        except ValidationError as e:
            return error(str(e), 400)

        scan_index_forward = query_params.sort_order == "asc"

        key_condition = Key("PK").eq(f"ASSET#{asset_id}") & Key("SK").begins_with(
            "DISPOSAL#"
        )

        filter_exp = None
        if query_params.status:
            filter_exp = Attr("DisposalStatusIndexPK").eq(
                f"DISPOSAL_STATUS#{query_params.status}"
            )

        items, next_cursor = paginated_query(
            table,
            None,
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
            raw_status = item.get("DisposalStatusIndexPK") or ""
            disposal_status = raw_status.replace("DISPOSAL_STATUS#", "")
            if not disposal_status:
                continue

            list_item = AssetDisposalListItem(
                asset_id=item["PK"].replace("ASSET#", ""),
                disposal_id=item.get("DisposalID", item["SK"].replace("DISPOSAL#", "")),
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
