import os
from datetime import datetime, timezone

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.types import TypeSerializer
from pydantic import ValidationError

from custom_exceptions import NotFoundException, ConflictException
from utils import success, error, get_item
from utils.auth import require_group
from utils.enums import Asset_Status_Enum, Issue_Status_Enum, User_Role_Enum

from model import ManagementReviewIssueRequest, ManagementReviewIssueResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]
EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "default")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
dynamodb_client = boto3.client("dynamodb")
eventbridge_client = boto3.client("events")
serializer = TypeSerializer()


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id = require_group(event, User_Role_Enum.MANAGEMENT)

        asset_id = event["pathParameters"]["asset_id"]
        issue_id = event["pathParameters"]["issue_id"]

        body = json.loads(event.get("body") or "{}")
        request = ManagementReviewIssueRequest(**body)

        # Fetch asset metadata (validate asset exists)
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        # Fetch issue record
        issue_item = get_item(
            table, {"PK": f"ASSET#{asset_id}", "SK": f"ISSUE#{issue_id}"}
        )
        if not issue_item:
            raise NotFoundException("Issue record not found")

        # Verify issue is in REPLACEMENT_REQUIRED status
        if issue_item["Status"] != Issue_Status_Enum.REPLACEMENT_REQUIRED:
            raise ConflictException(
                "This issue does not have a pending replacement request"
            )

        # Determine new status based on decision
        status_map = {
            "APPROVE": Issue_Status_Enum.REPLACEMENT_APPROVED,
            "REJECT": Issue_Status_Enum.REPLACEMENT_REJECTED,
        }
        new_status = status_map[request.decision]

        review_now = datetime.now(timezone.utc).isoformat()

        # Build issue update fields
        issue_update_fields = {
            "Status": new_status,
            "ManagementReviewedBy": actor_id,
            "ManagementReviewedAt": review_now,
        }
        if request.decision == "APPROVE" and request.remarks:
            issue_update_fields["ManagementRemarks"] = request.remarks
        elif request.decision == "REJECT":
            issue_update_fields["ManagementRejectionReason"] = request.rejection_reason

        # Build UpdateExpression with SET and REMOVE (clear GSI keys)
        set_parts = [f"#{k} = :{k}" for k in issue_update_fields]
        issue_update_expr = "SET " + ", ".join(set_parts) + " REMOVE #isipk, #isisk"
        issue_expr_names = {f"#{k}": k for k in issue_update_fields}
        issue_expr_names["#isipk"] = "IssueStatusIndexPK"
        issue_expr_names["#isisk"] = "IssueStatusIndexSK"
        issue_expr_values = {
            f":{k}": serializer.serialize(v) for k, v in issue_update_fields.items()
        }

        # Build transaction items
        transact_items = [
            {
                "Update": {
                    "TableName": ASSETS_TABLE,
                    "Key": {
                        "PK": serializer.serialize(f"ASSET#{asset_id}"),
                        "SK": serializer.serialize(f"ISSUE#{issue_id}"),
                    },
                    "UpdateExpression": issue_update_expr,
                    "ExpressionAttributeNames": issue_expr_names,
                    "ExpressionAttributeValues": issue_expr_values,
                }
            },
        ]

        # On REJECT: reset asset to IN_STOCK and unlink from employee
        if request.decision == "REJECT":
            asset_update_expr = (
                "SET #status = :status, #sipk = :sipk " "REMOVE #eaipk, #eaisk"
            )
            asset_attr_names = {
                "#status": "Status",
                "#sipk": "StatusIndexPK",
                "#eaipk": "EmployeeAssetIndexPK",
                "#eaisk": "EmployeeAssetIndexSK",
            }
            asset_attr_values = {
                ":status": serializer.serialize(Asset_Status_Enum.IN_STOCK),
                ":sipk": serializer.serialize(
                    f"STATUS#{Asset_Status_Enum.IN_STOCK.value}"
                ),
            }
            transact_items.append(
                {
                    "Update": {
                        "TableName": ASSETS_TABLE,
                        "Key": {
                            "PK": serializer.serialize(f"ASSET#{asset_id}"),
                            "SK": serializer.serialize("METADATA"),
                        },
                        "UpdateExpression": asset_update_expr,
                        "ExpressionAttributeNames": asset_attr_names,
                        "ExpressionAttributeValues": asset_attr_values,
                    }
                }
            )

        dynamodb_client.transact_write_items(TransactItems=transact_items)

        response = ManagementReviewIssueResponse(
            asset_id=asset_id,
            issue_id=issue_id,
            status=new_status,
        )

        # Emit EventBridge event on REPLACEMENT_APPROVED to trigger Phase 5 Return Process
        if new_status == Issue_Status_Enum.REPLACEMENT_APPROVED:
            try:
                eventbridge_client.put_events(
                    Entries=[
                        {
                            "Source": "gms.issue-management",
                            "DetailType": "ReplacementApproved",
                            "Detail": json.dumps(
                                {
                                    "asset_id": asset_id,
                                    "issue_id": issue_id,
                                    "approved_by": actor_id,
                                    "approved_at": review_now,
                                    "remarks": request.remarks or "",
                                }
                            ),
                            "EventBusName": EVENT_BUS_NAME,
                        }
                    ]
                )
            except Exception:
                logger.exception(
                    "EventBridge event emission failed — approval still succeeded"
                )

        return success(response.model_dump())

    except ValidationError as e:
        return error(str(e), 400)
    except PermissionError as e:
        return error(str(e), 403)
    except NotFoundException as e:
        return error(str(e), 404)
    except ConflictException as e:
        return error(str(e), 409)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
