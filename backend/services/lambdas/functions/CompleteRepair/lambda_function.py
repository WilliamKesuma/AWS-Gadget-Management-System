import os
from datetime import datetime, timezone

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer

from custom_exceptions import NotFoundException, ConflictException
from utils import success, error, get_item, check_record_lock
from utils.auth import require_group
from utils.enums import Asset_Status_Enum, Issue_Status_Enum, User_Role_Enum

from model import CompleteRepairRequest, CompleteRepairResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
dynamodb_client = boto3.client("dynamodb")


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id = require_group(event, User_Role_Enum.IT_ADMIN)

        asset_id = event["pathParameters"]["asset_id"]
        issue_id = event["pathParameters"]["issue_id"]

        # Parse optional body
        body = json.loads(event.get("body") or "{}")
        request = CompleteRepairRequest(**body)

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        # Check record lock before any other validation
        check_record_lock(asset_item)

        # Check asset is in UNDER_REPAIR status
        if asset_item["Status"] != Asset_Status_Enum.UNDER_REPAIR:
            raise ConflictException("Asset is not in a repairable status")

        # Fetch issue record
        issue_item = get_item(
            table, {"PK": f"ASSET#{asset_id}", "SK": f"ISSUE#{issue_id}"}
        )
        if not issue_item:
            raise NotFoundException("Issue record not found")

        now = datetime.now(timezone.utc).isoformat()

        # Build Issue_Record update expression dynamically
        update_expr_parts = [
            "#status = :new_status",
            "#completed_at = :completed_at",
            "#isipk = :isipk",
            "#isisk = :isisk",
        ]
        expr_attr_names = {
            "#status": "Status",
            "#completed_at": "CompletedAt",
            "#isipk": "IssueStatusIndexPK",
            "#isisk": "IssueStatusIndexSK",
        }
        expr_attr_values = {
            ":new_status": {"S": Issue_Status_Enum.RESOLVED},
            ":completed_at": {"S": now},
            ":isipk": {"S": f"ISSUE_STATUS#{Issue_Status_Enum.RESOLVED.value}"},
            ":isisk": {
                "S": f"ISSUE#{issue_item.get('IssueID', issue_item['SK'].replace('ISSUE#', ''))}"
            },
        }

        if request.completion_notes is not None:
            update_expr_parts.append("#completion_notes = :completion_notes")
            expr_attr_names["#completion_notes"] = "CompletionNotes"
            expr_attr_values[":completion_notes"] = {"S": request.completion_notes}

        update_expression = "SET " + ", ".join(update_expr_parts)

        # Determine post-repair status: if the asset still has an assigned
        # employee it goes back to ASSIGNED; otherwise (returned before repair)
        # it goes to IN_STOCK.
        has_employee = bool(asset_item.get("EmployeeAssetIndexPK"))
        post_repair_status = (
            Asset_Status_Enum.ASSIGNED if has_employee else Asset_Status_Enum.IN_STOCK
        )

        # TransactWriteItems: update Asset_Record + update Issue_Record
        dynamodb_client.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "TableName": ASSETS_TABLE,
                        "Key": {
                            "PK": {"S": f"ASSET#{asset_id}"},
                            "SK": {"S": "METADATA"},
                        },
                        "UpdateExpression": "SET #status = :new_status, #sipk = :sipk, #sisk = :sisk",
                        "ConditionExpression": "#status = :status1",
                        "ExpressionAttributeNames": {
                            "#status": "Status",
                            "#sipk": "StatusIndexPK",
                            "#sisk": "StatusIndexSK",
                        },
                        "ExpressionAttributeValues": {
                            ":new_status": {"S": post_repair_status},
                            ":status1": {"S": Asset_Status_Enum.UNDER_REPAIR},
                            ":sipk": {"S": f"STATUS#{post_repair_status.value}"},
                            ":sisk": {"S": f"ASSET#{asset_id}"},
                        },
                    }
                },
                {
                    "Update": {
                        "TableName": ASSETS_TABLE,
                        "Key": {
                            "PK": {"S": f"ASSET#{asset_id}"},
                            "SK": {"S": f"ISSUE#{issue_id}"},
                        },
                        "UpdateExpression": update_expression,
                        "ExpressionAttributeNames": expr_attr_names,
                        "ExpressionAttributeValues": expr_attr_values,
                    }
                },
            ]
        )

        response = CompleteRepairResponse(
            asset_id=asset_id,
            issue_id=issue_id,
            status=post_repair_status,
        )
        return success(response.model_dump())

    except PermissionError as e:
        return error(str(e), 403)
    except NotFoundException as e:
        return error(str(e), 404)
    except ConflictException as e:
        return error(str(e), 409)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
