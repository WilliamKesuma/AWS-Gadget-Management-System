import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Attr, Key
from pydantic import ValidationError

from utils import success, error
from utils.auth import get_caller_info
from utils.enums import Issue_Status_Enum, User_Role_Enum
from utils.pagination import PaginationInput, PaginatedResponse
from utils.ddb_helper import paginated_query
from utils.user_resolver import resolve_user_names, collect_user_ids

from model import ListAllIssuesParams, AllIssueListItem

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)

TERMINAL_ISSUE_STATUSES = {
    Issue_Status_Enum.RESOLVED.value,
    Issue_Status_Enum.REPLACEMENT_REJECTED.value,
}


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
            query_params = ListAllIssuesParams(
                sort_order=params.get("sort_order", "desc"),
                status=params.get("status"),
                category=params.get("category"),
                history=params.get("history", "false").lower() == "true",
                asset_id=params.get("asset_id"),
            )
        except ValidationError as e:
            return error(str(e), 400)

        scan_index_forward = query_params.sort_order == "asc"

        # Use IssueStatusIndex when status filter is provided, else IssueEntityIndex
        if query_params.status:
            key_condition = Key("IssueStatusIndexPK").eq(
                f"ISSUE_STATUS#{query_params.status}"
            )
            index_name = "IssueStatusIndex"
        else:
            key_condition = Key("IssueEntityType").eq("ISSUE")
            index_name = "IssueEntityIndex"

        # Build filter expression
        filter_exp = None

        # Employee: filter to own reported issues only
        if is_employee and not is_it_admin and not is_management:
            filter_exp = Attr("ReportedBy").eq(actor_id)

        # Optional category filter
        if query_params.category:
            cond = Attr("Category").eq(query_params.category.value)
            filter_exp = (filter_exp & cond) if filter_exp else cond

        # Asset ID filter
        if query_params.asset_id:
            cond = Attr("PK").eq(f"ASSET#{query_params.asset_id}")
            filter_exp = (filter_exp & cond) if filter_exp else cond

        # History filter: exclude terminal statuses when history=false
        if not query_params.history and not query_params.status:
            for terminal_status in TERMINAL_ISSUE_STATUSES:
                cond = Attr("Status").ne(terminal_status)
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
                    item["ReportedBy"],
                    item.get("ResolvedBy"),
                    item.get("ManagementReviewedBy"),
                )
            )
        names = resolve_user_names(table, all_user_ids)

        issue_items = []
        for item in items:
            list_item = AllIssueListItem(
                asset_id=item["PK"].replace("ASSET#", ""),
                issue_id=item.get("IssueID", item["SK"].replace("ISSUE#", "")),
                issue_description=item["IssueDescription"],
                category=item["Category"],
                status=item["Status"],
                action_path=item.get("ActionPath"),
                reported_by=names.get(item["ReportedBy"], item["ReportedBy"]),
                reported_by_id=item["ReportedBy"],
                created_at=item["CreatedAt"],
                resolved_by=(
                    names.get(item["ResolvedBy"]) if item.get("ResolvedBy") else None
                ),
                resolved_by_id=item.get("ResolvedBy"),
                resolved_at=item.get("ResolvedAt"),
                repair_notes=item.get("RepairNotes"),
                warranty_notes=item.get("WarrantyNotes"),
                warranty_sent_at=item.get("WarrantySentAt"),
                replacement_justification=item.get("ReplacementJustification"),
                management_reviewed_by=(
                    names.get(item["ManagementReviewedBy"])
                    if item.get("ManagementReviewedBy")
                    else None
                ),
                management_reviewed_by_id=item.get("ManagementReviewedBy"),
                management_reviewed_at=item.get("ManagementReviewedAt"),
                management_rejection_reason=item.get("ManagementRejectionReason"),
                management_remarks=item.get("ManagementRemarks"),
                completed_at=item.get("CompletedAt"),
                completion_notes=item.get("CompletionNotes"),
            )
            issue_items.append(list_item)

        response = PaginatedResponse(
            items=[item.model_dump() for item in issue_items],
            count=len(issue_items),
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
