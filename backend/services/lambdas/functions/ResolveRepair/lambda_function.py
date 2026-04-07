import os
from datetime import datetime, timezone

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer

from custom_exceptions import NotFoundException, ConflictException
from utils import success, error, get_item
from utils.auth import require_group
from utils.enums import Asset_Status_Enum, Issue_Status_Enum, User_Role_Enum

from model import ResolveRepairRequest, ResolveRepairResponse

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
        request = ResolveRepairRequest(**body)

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        # Check asset is in ISSUE_REPORTED status (asset domain — Asset_Status_Enum)
        if asset_item["Status"] != Asset_Status_Enum.ISSUE_REPORTED:
            raise ConflictException("Asset is not in ISSUE_REPORTED status")

        # Fetch issue record
        issue_item = get_item(
            table, {"PK": f"ASSET#{asset_id}", "SK": f"ISSUE#{issue_id}"}
        )
        if not issue_item:
            raise NotFoundException("Issue record not found")

        # Verify issue record is in TROUBLESHOOTING status
        if issue_item["Status"] != Issue_Status_Enum.TROUBLESHOOTING:
            raise ConflictException("Issue is not in TROUBLESHOOTING status")

        now = datetime.now(timezone.utc).isoformat()

        # Build Issue_Record update expression dynamically
        update_expr_parts = [
            "#status = :new_status",
            "#resolved_by = :resolved_by",
            "#resolved_at = :resolved_at",
            "#isipk = :isipk",
            "#isisk = :isisk",
        ]
        expr_attr_names = {
            "#status": "Status",
            "#resolved_by": "ResolvedBy",
            "#resolved_at": "ResolvedAt",
            "#isipk": "IssueStatusIndexPK",
            "#isisk": "IssueStatusIndexSK",
        }
        expr_attr_values = {
            ":new_status": {"S": Issue_Status_Enum.UNDER_REPAIR},
            ":resolved_by": {"S": actor_id},
            ":resolved_at": {"S": now},
            ":isipk": {"S": f"ISSUE_STATUS#{Issue_Status_Enum.UNDER_REPAIR.value}"},
            ":isisk": {
                "S": f"ISSUE#{issue_item.get('IssueID', issue_item['SK'].replace('ISSUE#', ''))}"
            },
        }

        if request.repair_notes is not None:
            update_expr_parts.append("#repair_notes = :repair_notes")
            expr_attr_names["#repair_notes"] = "RepairNotes"
            expr_attr_values[":repair_notes"] = {"S": request.repair_notes}

        update_expression = "SET " + ", ".join(update_expr_parts)

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
                        "ConditionExpression": "#status = :expected_status",
                        "ExpressionAttributeNames": {
                            "#status": "Status",
                            "#sipk": "StatusIndexPK",
                            "#sisk": "StatusIndexSK",
                        },
                        "ExpressionAttributeValues": {
                            ":new_status": {"S": Asset_Status_Enum.UNDER_REPAIR},
                            ":expected_status": {"S": Asset_Status_Enum.ISSUE_REPORTED},
                            ":sipk": {
                                "S": f"STATUS#{Asset_Status_Enum.UNDER_REPAIR.value}"
                            },
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

        response = ResolveRepairResponse(
            asset_id=asset_id,
            issue_id=issue_id,
            status=Issue_Status_Enum.UNDER_REPAIR,
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
