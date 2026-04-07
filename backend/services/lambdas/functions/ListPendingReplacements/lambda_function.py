import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Attr, Key
from pydantic import ValidationError

from utils import success, error
from utils.auth import require_group
from utils.enums import Issue_Status_Enum, User_Role_Enum
from utils.pagination import PaginationInput, PaginatedResponse
from utils.ddb_helper import paginated_query
from utils.user_resolver import resolve_user_names, collect_user_ids

from model import ListPendingReplacementsParams, PendingReplacementListItem

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)

# Statuses to include when history=true (past management decisions)
HISTORY_REPLACEMENT_STATUSES = {
    Issue_Status_Enum.REPLACEMENT_REQUIRED.value,
    Issue_Status_Enum.REPLACEMENT_APPROVED.value,
    Issue_Status_Enum.REPLACEMENT_REJECTED.value,
}


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id = require_group(event, User_Role_Enum.MANAGEMENT)

        params = event.get("queryStringParameters") or {}

        pagination = PaginationInput.from_query_params(params)

        try:
            query_params = ListPendingReplacementsParams(
                sort_order=params.get("sort_order", "desc"),
                history=params.get("history", "false").lower() == "true",
            )
        except ValidationError as e:
            return error(str(e), 400)

        scan_index_forward = query_params.sort_order == "asc"

        if query_params.history:
            # History mode: query all issues, filter to replacement-related statuses
            key_condition = Key("IssueEntityType").eq("ISSUE")
            index_name = "IssueEntityIndex"

            # Filter to only replacement-related statuses
            filter_exp = (
                Attr("Status").eq(Issue_Status_Enum.REPLACEMENT_REQUIRED.value)
                | Attr("Status").eq(Issue_Status_Enum.REPLACEMENT_APPROVED.value)
                | Attr("Status").eq(Issue_Status_Enum.REPLACEMENT_REJECTED.value)
            )
        else:
            # Default: only REPLACEMENT_REQUIRED (needs action)
            key_condition = Key("IssueStatusIndexPK").eq(
                "ISSUE_STATUS#REPLACEMENT_REQUIRED"
            )
            index_name = "IssueStatusIndex"
            filter_exp = None

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
                    item["ReportedBy"],
                    item.get("ResolvedBy"),
                    item.get("ManagementReviewedBy"),
                )
            )
        names = resolve_user_names(table, all_user_ids)

        pending_items = []
        for item in items:
            resolved_by_id = item.get("ResolvedBy")
            list_item = PendingReplacementListItem(
                asset_id=item["PK"].replace("ASSET#", ""),
                issue_id=item.get("IssueID", item["SK"].replace("ISSUE#", "")),
                issue_description=item["IssueDescription"],
                reported_by=names.get(item["ReportedBy"], item["ReportedBy"]),
                reported_by_id=item["ReportedBy"],
                created_at=item["CreatedAt"],
                resolved_by=(
                    names.get(resolved_by_id, resolved_by_id)
                    if resolved_by_id
                    else None
                ),
                resolved_by_id=resolved_by_id,
                resolved_at=item.get("ResolvedAt"),
                replacement_justification=item.get("ReplacementJustification"),
                status=item["Status"],
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
            pending_items.append(list_item)

        response = PaginatedResponse(
            items=[item.model_dump() for item in pending_items],
            count=len(pending_items),
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
