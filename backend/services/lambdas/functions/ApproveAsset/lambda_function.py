import os
from datetime import datetime, timezone

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from pydantic import ValidationError

from custom_exceptions import ConflictException, NotFoundException
from utils import error, get_item, success
from utils.auth import require_group
from utils.enums import Asset_Status_Enum, User_Role_Enum
from utils.models import AssetMetadataModel, AuditLogModel

from model import ApproveAssetRequest, ApproveAssetResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id = require_group(event, User_Role_Enum.MANAGEMENT)

        asset_id = event["pathParameters"]["asset_id"]

        body = json.loads(event.get("body") or "{}")
        request = ApproveAssetRequest(**body)

        # Fetch asset
        item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not item:
            raise NotFoundException("Asset not found")

        asset = AssetMetadataModel(**item)

        if asset.Status != Asset_Status_Enum.ASSET_PENDING_APPROVAL:
            raise ConflictException("Asset is not in a pending approval state")

        new_status = (
            Asset_Status_Enum.IN_STOCK
            if request.action == "APPROVE"
            else Asset_Status_Enum.ASSET_REJECTED
        )

        now = datetime.now(timezone.utc).isoformat()

        # Build update expression
        update_fields = {
            "#Status": new_status.value,
            "#StatusIndexPK": f"STATUS#{new_status.value}",
            "#StatusIndexSK": f"ASSET#{asset_id}",
        }
        expr_names = {
            "#Status": "Status",
            "#StatusIndexPK": "StatusIndexPK",
            "#StatusIndexSK": "StatusIndexSK",
        }
        expr_values = {
            ":status": new_status.value,
            ":sip": f"STATUS#{new_status.value}",
            ":sis": f"ASSET#{asset_id}",
        }
        set_parts = [
            "#Status = :status",
            "#StatusIndexPK = :sip",
            "#StatusIndexSK = :sis",
        ]

        if request.action == "APPROVE" and request.remarks:
            set_parts.append("#Remarks = :remarks")
            expr_names["#Remarks"] = "Remarks"
            expr_values[":remarks"] = request.remarks
        elif request.action == "REJECT":
            set_parts.append("#RejectionReason = :rejection_reason")
            expr_names["#RejectionReason"] = "RejectionReason"
            expr_values[":rejection_reason"] = request.rejection_reason

        # Build audit log
        audit = AuditLogModel(
            PK=f"ASSET#{asset_id}",
            SK=f"LOG#{now}#{actor_id}",
            ActorID=actor_id,
            Phase="ASSET_APPROVAL",
            PreviousStatus=Asset_Status_Enum.ASSET_PENDING_APPROVAL.value,
            NewStatus=new_status.value,
            RejectionReason=(
                request.rejection_reason if request.action == "REJECT" else None
            ),
            Remarks=request.remarks if request.action == "APPROVE" else None,
        )

        # Add condition guard: status must still be ASSET_PENDING_APPROVAL at write time
        expr_names["#ExpectedStatus"] = "Status"
        expr_values[":expected_status"] = Asset_Status_Enum.ASSET_PENDING_APPROVAL.value

        # Transact: update asset + put audit log
        table.meta.client.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "TableName": table.name,
                        "Key": {"PK": f"ASSET#{asset_id}", "SK": "METADATA"},
                        "UpdateExpression": "SET " + ", ".join(set_parts),
                        "ConditionExpression": "#ExpectedStatus = :expected_status",
                        "ExpressionAttributeNames": expr_names,
                        "ExpressionAttributeValues": expr_values,
                    }
                },
                {
                    "Put": {
                        "TableName": table.name,
                        "Item": audit.model_dump(exclude_none=True),
                    }
                },
            ]
        )

        return success(
            ApproveAssetResponse(
                asset_id=asset_id,
                status=new_status.value,
            ).model_dump()
        )

    except ValidationError as e:
        return error(str(e), 400)
    except PermissionError as e:
        return error(str(e), 403)
    except NotFoundException as e:
        return error(str(e), 404)
    except ConflictException as e:
        return error(str(e), 409)
    except table.meta.client.exceptions.TransactionCanceledException:
        return error("Asset status changed concurrently. Please retry.", 409)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
