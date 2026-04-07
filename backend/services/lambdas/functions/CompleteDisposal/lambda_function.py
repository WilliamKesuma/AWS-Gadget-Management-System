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
    Finance_Notification_Status_Enum,
    User_Role_Enum,
)
from utils.models import AuditLogModel

from model import CompleteDisposalRequest, CompleteDisposalResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]
FINANCE_NOTIFICATION_QUEUE_URL = os.environ["FINANCE_NOTIFICATION_QUEUE_URL"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
dynamodb_client = boto3.client("dynamodb")
sqs_client = boto3.client("sqs")
serializer = TypeSerializer()


def _serialize_item(item: dict) -> dict:
    """Convert a Python dict to DynamoDB JSON format."""
    return {k: serializer.serialize(v) for k, v in item.items() if v is not None}


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id = require_group(event, User_Role_Enum.IT_ADMIN)

        asset_id = event["pathParameters"]["asset_id"]
        disposal_id = event["pathParameters"]["disposal_id"]

        body = json.loads(event.get("body") or "{}")
        request = CompleteDisposalRequest(**body)

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

        # Validate management has approved (ManagementApprovedAt must exist on disposal record)
        if not disposal_record.get("ManagementApprovedAt"):
            raise ConflictException(
                "Disposal has not been approved by management. ManagementApprovedAt is required"
            )

        # Validate DataWipeConfirmed is true
        if not request.data_wipe_confirmed:
            raise ConflictException(
                "Data wipe must be confirmed before disposal can be completed"
            )

        now = datetime.now(timezone.utc).isoformat()

        # Build asset update: status=DISPOSED, IsLocked=true, StatusIndexPK
        # Also unlink the assigned employee by removing EmployeeAssetIndex GSI keys
        # Guard: status must still be DISPOSAL_PENDING at write time
        asset_update = {
            "Update": {
                "TableName": ASSETS_TABLE,
                "Key": {
                    "PK": serializer.serialize(f"ASSET#{asset_id}"),
                    "SK": serializer.serialize("METADATA"),
                },
                "UpdateExpression": "SET #status = :status, #sipk = :sipk, #locked = :locked REMOVE #eapk, #eask",
                "ConditionExpression": "#status = :expected_status",
                "ExpressionAttributeNames": {
                    "#status": "Status",
                    "#sipk": "StatusIndexPK",
                    "#locked": "IsLocked",
                    "#eapk": "EmployeeAssetIndexPK",
                    "#eask": "EmployeeAssetIndexSK",
                },
                "ExpressionAttributeValues": {
                    ":status": serializer.serialize(Asset_Status_Enum.DISPOSED),
                    ":sipk": serializer.serialize(
                        f"STATUS#{Asset_Status_Enum.DISPOSED.value}"
                    ),
                    ":locked": serializer.serialize(True),
                    ":expected_status": serializer.serialize(
                        Asset_Status_Enum.DISPOSAL_PENDING
                    ),
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
                "UpdateExpression": (
                    "SET #cb = :cb, #ca = :ca, #dd = :dd, #dwc = :dwc, "
                    "#locked = :locked, #fns = :fns, #fnst = :fnst, #dsipk = :dsipk, #dsisk = :dsisk"
                ),
                "ExpressionAttributeNames": {
                    "#cb": "CompletedBy",
                    "#ca": "CompletedAt",
                    "#dd": "DisposalDate",
                    "#dwc": "DataWipeConfirmed",
                    "#locked": "IsLocked",
                    "#fns": "FinanceNotificationSent",
                    "#fnst": "FinanceNotificationStatus",
                    "#dsipk": "DisposalStatusIndexPK",
                    "#dsisk": "DisposalStatusIndexSK",
                },
                "ExpressionAttributeValues": {
                    ":cb": serializer.serialize(actor_id),
                    ":ca": serializer.serialize(now),
                    ":dd": serializer.serialize(request.disposal_date),
                    ":dwc": serializer.serialize(True),
                    ":locked": serializer.serialize(True),
                    ":fns": serializer.serialize(False),
                    ":fnst": serializer.serialize(
                        Finance_Notification_Status_Enum.QUEUED
                    ),
                    ":dsipk": serializer.serialize(
                        f"DISPOSAL_STATUS#{Asset_Status_Enum.DISPOSED.value}"
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
            NewStatus=Asset_Status_Enum.DISPOSED,
        )
        audit_item = _serialize_item(audit_log.model_dump())

        # TransactWriteItems: update Asset_Record, update Disposal_Record, put Audit_Log
        dynamodb_client.transact_write_items(
            TransactItems=[
                asset_update,
                disposal_update,
                {"Put": {"TableName": ASSETS_TABLE, "Item": audit_item}},
            ]
        )

        # Send SQS message with financial payload
        asset_specs = disposal_record.get("AssetSpecs") or {}
        sqs_message = {
            "asset_id": asset_id,
            "serial_number": asset_specs.get("SerialNumber"),
            "purchase_date": asset_specs.get("PurchaseDate"),
            "original_cost": asset_specs.get("Cost"),
            "disposal_date": request.disposal_date,
            "disposal_reason": disposal_record.get("DisposalReason"),
        }
        sqs_client.send_message(
            QueueUrl=FINANCE_NOTIFICATION_QUEUE_URL,
            MessageBody=json.dumps(sqs_message),
        )

        response = CompleteDisposalResponse(
            asset_id=asset_id,
            disposal_id=disposal_record.get(
                "DisposalID", disposal_sk.replace("DISPOSAL#", "")
            ),
            status=Asset_Status_Enum.DISPOSED,
            finance_notification_status=Finance_Notification_Status_Enum.QUEUED,
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
    except dynamodb_client.exceptions.TransactionCanceledException:
        return error("Asset status changed concurrently. Please retry.", 409)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
