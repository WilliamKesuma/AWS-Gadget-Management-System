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

from model import IssueListItem, ListIssuesParams

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)


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

        try:
            query_params = ListIssuesParams(
                sort_order=params.get("sort_order", "desc"),
                status=params.get("status"),
            )
        except ValidationError as e:
            return error(str(e), 400)

        scan_index_forward = query_params.sort_order == "asc"

        # Query issue records with pagination
        key_condition = Key("PK").eq(f"ASSET#{asset_id}") & Key("SK").begins_with(
            "ISSUE#"
        )

        filter_exp = None

        # Employees only see their own reported issues
        if is_employee and not is_it_admin and not is_management:
            filter_exp = Attr("ReportedBy").eq(actor_id)

        if query_params.status:
            cond = Attr("Status").eq(query_params.status)
            filter_exp = (filter_exp & cond) if filter_exp else cond

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
                    item["ReportedBy"],
                    item.get("ResolvedBy"),
                    item.get("ManagementReviewedBy"),
                )
            )
        names = resolve_user_names(table, all_user_ids)

        # Map each item to response model
        issue_items = []
        for item in items:
            list_item = IssueListItem(
                asset_id=item["PK"].replace("ASSET#", ""),
                issue_id=item.get("IssueID", item["SK"].replace("ISSUE#", "")),
                issue_description=item["IssueDescription"],
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
    except NotFoundException as e:
        return error(str(e), 404)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
