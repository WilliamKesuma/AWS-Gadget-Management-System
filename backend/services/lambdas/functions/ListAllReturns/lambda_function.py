import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Attr, Key
from pydantic import ValidationError

from utils import success, error
from utils.auth import get_caller_info
from utils.enums import Maintenance_Record_Type_Enum, Return_Status_Enum, User_Role_Enum
from utils.pagination import PaginationInput, PaginatedResponse
from utils.ddb_helper import paginated_query
from utils.user_resolver import resolve_user_names, collect_user_ids

from model import ListAllReturnsParams, AllReturnListItem

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)

MAINTENANCE_ENTITY_INDEX = "MaintenanceEntityIndex"


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id, groups = get_caller_info(event)

        is_it_admin = User_Role_Enum.IT_ADMIN in groups
        is_management = User_Role_Enum.MANAGEMENT in groups
        is_employee = User_Role_Enum.EMPLOYEE in groups

        if is_employee and not is_it_admin and not is_management:
            raise PermissionError("Employees cannot list global returns")

        if not is_it_admin and not is_management:
            raise PermissionError("Insufficient permissions")

        params = event.get("queryStringParameters") or {}

        pagination = PaginationInput.from_query_params(params)

        try:
            query_params = ListAllReturnsParams(
                sort_order=params.get("sort_order", "desc"),
                status=params.get("status"),
                return_trigger=params.get("return_trigger"),
                condition_assessment=params.get("condition_assessment"),
                history=params.get("history", "false").lower() == "true",
                asset_id=params.get("asset_id"),
            )
        except ValidationError as e:
            return error(str(e), 400)

        scan_index_forward = query_params.sort_order == "asc"

        # Query MaintenanceEntityIndex, filter to RETURN records only
        key_condition = Key("MaintenanceEntityType").eq("MAINTENANCE")

        filter_exp = Attr("MaintenanceRecordType").eq(
            Maintenance_Record_Type_Enum.RETURN.value
        )

        # Status filter
        if query_params.status:
            if query_params.status == Return_Status_Enum.RETURN_PENDING.value:
                filter_exp = filter_exp & Attr("ResolvedStatus").not_exists()
            else:
                filter_exp = filter_exp & Attr("ResolvedStatus").eq(query_params.status)
        elif not query_params.history:
            # Active only: exclude COMPLETED returns
            filter_exp = filter_exp & (
                Attr("ResolvedStatus").not_exists()
                | Attr("ResolvedStatus").ne(Return_Status_Enum.COMPLETED.value)
            )

        # Asset ID filter
        if query_params.asset_id:
            filter_exp = filter_exp & Attr("PK").eq(f"ASSET#{query_params.asset_id}")

        if query_params.return_trigger:
            filter_exp = filter_exp & Attr("ReturnTrigger").eq(
                query_params.return_trigger.value
            )
        if query_params.condition_assessment:
            filter_exp = filter_exp & Attr("ConditionAssessment").eq(
                query_params.condition_assessment.value
            )

        items, next_cursor = paginated_query(
            table,
            MAINTENANCE_ENTITY_INDEX,
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
                    item.get("InitiatedBy"),
                    item.get("CompletedBy"),
                )
            )
        names = resolve_user_names(table, all_user_ids)

        return_items = []
        for item in items:
            list_item = AllReturnListItem(
                asset_id=item["PK"].replace("ASSET#", ""),
                return_id=item.get("ReturnID", item["SK"].replace("RETURN#", "")),
                return_trigger=item["ReturnTrigger"],
                initiated_by=names.get(item["InitiatedBy"], item["InitiatedBy"]),
                initiated_by_id=item["InitiatedBy"],
                initiated_at=item["InitiatedAt"],
                condition_assessment=item["ConditionAssessment"],
                remarks=item["Remarks"],
                reset_status=item["ResetStatus"],
                serial_number=item.get("SerialNumber"),
                model=item.get("Model"),
                resolved_status=item.get("ResolvedStatus"),
                completed_at=item.get("CompletedAt"),
                completed_by=(
                    names.get(item["CompletedBy"]) if item.get("CompletedBy") else None
                ),
                completed_by_id=item.get("CompletedBy"),
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
