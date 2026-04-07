import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key, Attr
from pydantic import ValidationError

from utils import success, error
from utils.auth import get_caller_info
from utils.enums import Return_Status_Enum, User_Role_Enum
from utils.pagination import PaginationInput, PaginatedResponse
from utils.ddb_helper import paginated_query
from utils.user_resolver import resolve_user_names, collect_user_ids

from model import ListReturnsParams, ReturnListItem

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
            raise PermissionError("Employees cannot list returns")

        if not is_it_admin and not is_management:
            raise PermissionError("Insufficient permissions")

        asset_id = event["pathParameters"]["asset_id"]

        params = event.get("queryStringParameters") or {}

        pagination = PaginationInput.from_query_params(params)

        # Build key condition for main table query
        key_condition = Key("PK").eq(f"ASSET#{asset_id}") & Key("SK").begins_with(
            "RETURN#"
        )

        try:
            query_params = ListReturnsParams(
                sort_order=params.get("sort_order", "desc"),
                return_trigger=params.get("return_trigger"),
                condition_assessment=params.get("condition_assessment"),
            )
        except ValidationError as e:
            return error(str(e), 400)

        scan_index_forward = query_params.sort_order == "asc"

        # Build filter expression based on status query parameter
        status_filter = params.get("status")
        filter_exp = None

        if status_filter:
            if status_filter == Return_Status_Enum.RETURN_PENDING:
                filter_exp = Attr("ResolvedStatus").not_exists()
            else:
                filter_exp = Attr("ResolvedStatus").eq(status_filter)

        if query_params.return_trigger:
            cond = Attr("ReturnTrigger").eq(query_params.return_trigger)
            filter_exp = (filter_exp & cond) if filter_exp else cond
        if query_params.condition_assessment:
            cond = Attr("ConditionAssessment").eq(query_params.condition_assessment)
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
            all_user_ids.update(collect_user_ids(item["InitiatedBy"]))
        names = resolve_user_names(table, all_user_ids)

        # Map each item to response model
        return_items = []
        for item in items:
            list_item = ReturnListItem(
                asset_id=item["PK"].replace("ASSET#", ""),
                return_id=item.get("ReturnID", item["SK"].replace("RETURN#", "")),
                return_trigger=item["ReturnTrigger"],
                initiated_by=names.get(item["InitiatedBy"], item["InitiatedBy"]),
                initiated_by_id=item["InitiatedBy"],
                initiated_at=item["InitiatedAt"],
                condition_assessment=item["ConditionAssessment"],
                remarks=item["Remarks"],
                reset_status=item["ResetStatus"],
                resolved_status=item.get("ResolvedStatus"),
                completed_at=item.get("CompletedAt"),
            )
            return_items.append(list_item)

        response = PaginatedResponse(
            items=[item.model_dump() for item in return_items],
            count=len(return_items),
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
