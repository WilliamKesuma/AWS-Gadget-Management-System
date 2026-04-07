import os
from datetime import datetime, timezone

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.types import TypeSerializer
from pydantic import ValidationError

from custom_exceptions import ConflictException, NotFoundException
from utils import error, get_item, success, check_record_lock
from utils.auth import require_group
from utils.enums import (
    Asset_Status_Enum,
    Email_Event_Type_Enum,
    User_Role_Enum,
)
from utils.models import AuditLogModel
from utils.email_queue import send_email_event

from model import ManagementReviewRequest, ManagementReviewResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
dynamodb_client = boto3.client("dynamodb")
serializer = TypeSerializer()


def _serialize_item(item: dict) -> dict:
    """Convert a Python dict to DynamoDB JSON format."""
    return {k: serializer.serialize(v) for k, v in item.items() if v is not None}


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id = require_group(event, User_Role_Enum.MANAGEMENT)

        asset_id = event["pathParameters"]["asset_id"]
        disposal_id = event["pathParameters"]["disposal_id"]

        body = json.loads(event.get("body") or "{}")
        request = ManagementReviewRequest(**body)

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        # Check asset record lock before any other validation
        check_record_lock(asset_item)

        # Fetch disposal record directly by UUID
        disposal_record = get_item(
            table, {"PK": f"ASSET#{asset_id}", "SK": f"DISPOSAL#{disposal_id}"}
        )
        if not disposal_record:
            raise NotFoundException("Disposal record not found")

        disposal_sk = disposal_record["SK"]

        # Check disposal record lock before any other validation
        check_record_lock(disposal_record, "disposal")

        # Validate asset is in DISPOSAL_PENDING status
        if asset_item["Status"] != Asset_Status_Enum.DISPOSAL_PENDING:
            raise ConflictException("Asset is not in DISPOSAL_PENDING status")

        # Validate rejection_reason for REJECT decision
        if request.decision == "REJECT":
            if not request.rejection_reason or not request.rejection_reason.strip():
                raise ValueError("Rejection reason is required")

        now = datetime.now(timezone.utc).isoformat()

        if request.decision == "APPROVE":
            new_status = Asset_Status_Enum.DISPOSAL_PENDING

            # Build disposal record update (asset stays DISPOSAL_PENDING,
            # ManagementApprovedAt timestamp signals approval)
            disposal_update_expr = "SET #mrb = :mrb, #mra = :mra, #maat = :maat, #dsipk = :dsipk, #dsisk = :dsisk"
            disposal_attr_names = {
                "#mrb": "ManagementReviewedBy",
                "#mra": "ManagementReviewedAt",
                "#maat": "ManagementApprovedAt",
                "#dsipk": "DisposalStatusIndexPK",
                "#dsisk": "DisposalStatusIndexSK",
            }
            disposal_attr_values = {
                ":mrb": serializer.serialize(actor_id),
                ":mra": serializer.serialize(now),
                ":maat": serializer.serialize(now),
                ":dsipk": serializer.serialize(
                    f"DISPOSAL_STATUS#{Asset_Status_Enum.DISPOSAL_PENDING.value}"
                ),
                ":dsisk": serializer.serialize(f"DISPOSAL#{disposal_id}"),
            }

            # Add optional remarks
            if request.remarks:
                disposal_update_expr += ", #mr = :mr"
                disposal_attr_names["#mr"] = "ManagementRemarks"
                disposal_attr_values[":mr"] = serializer.serialize(request.remarks)

            disposal_update = {
                "Update": {
                    "TableName": ASSETS_TABLE,
                    "Key": {
                        "PK": serializer.serialize(f"ASSET#{asset_id}"),
                        "SK": serializer.serialize(disposal_sk),
                    },
                    "UpdateExpression": disposal_update_expr,
                    "ExpressionAttributeNames": disposal_attr_names,
                    "ExpressionAttributeValues": disposal_attr_values,
                }
            }

            # Build audit log
            audit_log = AuditLogModel(
                PK=f"ASSET#{asset_id}",
                SK=f"LOG#{now}#{actor_id}",
                ActorID=actor_id,
                Phase="ASSET_DISPOSAL",
                PreviousStatus=Asset_Status_Enum.DISPOSAL_PENDING,
                NewStatus=Asset_Status_Enum.DISPOSAL_PENDING,
                Remarks=request.remarks,
            )

        else:
            # REJECT
            new_status = Asset_Status_Enum.IN_STOCK

            # Build asset update — set IN_STOCK, record RejectionReason, unlink employee
            asset_update = {
                "Update": {
                    "TableName": ASSETS_TABLE,
                    "Key": {
                        "PK": serializer.serialize(f"ASSET#{asset_id}"),
                        "SK": serializer.serialize("METADATA"),
                    },
                    "UpdateExpression": "SET #status = :status, #sipk = :sipk, #rr = :rr REMOVE #eaipk, #eaisk",
                    "ExpressionAttributeNames": {
                        "#status": "Status",
                        "#sipk": "StatusIndexPK",
                        "#rr": "RejectionReason",
                        "#eaipk": "EmployeeAssetIndexPK",
                        "#eaisk": "EmployeeAssetIndexSK",
                    },
                    "ExpressionAttributeValues": {
                        ":status": serializer.serialize(Asset_Status_Enum.IN_STOCK),
                        ":sipk": serializer.serialize(
                            f"STATUS#{Asset_Status_Enum.IN_STOCK.value}"
                        ),
                        ":rr": serializer.serialize(request.rejection_reason),
                    },
                }
            }

            # Build disposal record update
            disposal_update = {
                "Update": {
                    "TableName": ASSETS_TABLE,
                    "Key": {
                        "PK": serializer.serialize(f"ASSET#{asset_id}"),
                        "SK": serializer.serialize(disposal_sk),
                    },
                    "UpdateExpression": "SET #mrb = :mrb, #mra = :mra, #mrr = :mrr, #dsipk = :dsipk, #dsisk = :dsisk",
                    "ExpressionAttributeNames": {
                        "#mrb": "ManagementReviewedBy",
                        "#mra": "ManagementReviewedAt",
                        "#mrr": "ManagementRejectionReason",
                        "#dsipk": "DisposalStatusIndexPK",
                        "#dsisk": "DisposalStatusIndexSK",
                    },
                    "ExpressionAttributeValues": {
                        ":mrb": serializer.serialize(actor_id),
                        ":mra": serializer.serialize(now),
                        ":mrr": serializer.serialize(request.rejection_reason),
                        ":dsipk": serializer.serialize(
                            f"DISPOSAL_STATUS#{Asset_Status_Enum.DISPOSAL_REJECTED.value}"
                        ),
                        ":dsisk": serializer.serialize(f"DISPOSAL#{disposal_id}"),
                    },
                }
            }

            # Build audit log
            audit_log = AuditLogModel(
                PK=f"ASSET#{asset_id}",
                SK=f"LOG#{now}#{actor_id}",
                ActorID=actor_id,
                Phase="ASSET_DISPOSAL",
                PreviousStatus=Asset_Status_Enum.DISPOSAL_PENDING,
                NewStatus=Asset_Status_Enum.IN_STOCK,
                RejectionReason=request.rejection_reason,
            )

        audit_item = _serialize_item(audit_log.model_dump())

        if request.decision == "APPROVE":
            # No asset status change on approval — asset stays DISPOSAL_PENDING.
            # Only update disposal record and write audit log.
            dynamodb_client.transact_write_items(
                TransactItems=[
                    disposal_update,
                    {"Put": {"TableName": ASSETS_TABLE, "Item": audit_item}},
                ]
            )
        else:
            # REJECT: update asset status + disposal record + audit log
            dynamodb_client.transact_write_items(
                TransactItems=[
                    asset_update,
                    disposal_update,
                    {"Put": {"TableName": ASSETS_TABLE, "Item": audit_item}},
                ]
            )

        # On approval, notify IT admins via email that they can proceed with disposal
        if request.decision == "APPROVE":
            asset_specs = disposal_record.get("AssetSpecs") or {}
            send_email_event(
                Email_Event_Type_Enum.DISPOSAL_MANAGEMENT_APPROVED,
                asset_id=asset_id,
                disposal_id=disposal_record.get(
                    "DisposalID", disposal_sk.replace("DISPOSAL#", "")
                ),
                disposal_reason=disposal_record.get("DisposalReason", ""),
                justification=disposal_record.get("Justification", ""),
                brand=asset_specs.get("Brand"),
                model=asset_specs.get("Model"),
                serial_number=asset_specs.get("SerialNumber"),
            )

        response = ManagementReviewResponse(
            asset_id=asset_id,
            disposal_id=disposal_record.get(
                "DisposalID", disposal_sk.replace("DISPOSAL#", "")
            ),
            status=new_status,
        )
        return success(response.model_dump())

    except ValidationError as e:
        return error(str(e), 400)
    except ValueError as e:
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
