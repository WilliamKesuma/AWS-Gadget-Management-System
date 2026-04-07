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
    Maintenance_Record_Type_Enum,
    Reset_Status_Enum,
    User_Role_Enum,
)
from utils.models import AuditLogModel, ReturnRecordModel
from utils.id_generator import generate_domain_id

from model import InitiateReturnRequest, InitiateReturnResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
dynamodb_client = boto3.client("dynamodb")
serializer = TypeSerializer()


def _serialize_item(item: dict) -> dict:
    return {k: serializer.serialize(v) for k, v in item.items() if v is not None}


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id = require_group(event, User_Role_Enum.IT_ADMIN)

        asset_id = event["pathParameters"]["asset_id"]

        body = json.loads(event.get("body") or "{}")
        request = InitiateReturnRequest(**body)

        # Reject immediately if reset is incomplete
        if request.reset_status == Reset_Status_Enum.INCOMPLETE:
            raise ConflictException(
                "Device factory reset must be completed before the return can be initiated"
            )

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        check_record_lock(asset_item)

        if asset_item["Status"] != Asset_Status_Enum.ASSIGNED:
            raise ConflictException(
                "Asset is not in ASSIGNED status. Only assigned assets can be returned"
            )

        # Fetch serial number and model from asset record
        serial_number = asset_item.get("SerialNumber")
        model = asset_item.get("Model")

        return_id = generate_domain_id(table, "RETURN")
        now = datetime.now(timezone.utc).isoformat()

        # Build ReturnRecordModel — store condition/remarks/reset at initiation
        return_record = ReturnRecordModel(
            PK=f"ASSET#{asset_id}",
            SK=f"RETURN#{return_id}",
            ReturnID=return_id,
            ReturnTrigger=request.return_trigger,
            InitiatedBy=actor_id,
            InitiatedAt=now,
            SerialNumber=serial_number,
            Model=model,
            ConditionAssessment=request.condition_assessment,
            Remarks=request.remarks,
            ResetStatus=request.reset_status,
        )

        audit_log = AuditLogModel(
            PK=f"ASSET#{asset_id}",
            SK=f"LOG#{now}#{actor_id}",
            ActorID=actor_id,
            Phase="ASSET_RETURN",
            PreviousStatus=Asset_Status_Enum.ASSIGNED,
            NewStatus=Asset_Status_Enum.RETURN_PENDING,
        )

        return_item = _serialize_item(return_record.model_dump())
        audit_item = _serialize_item(audit_log.model_dump())

        dynamodb_client.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "TableName": ASSETS_TABLE,
                        "Key": {
                            "PK": serializer.serialize(f"ASSET#{asset_id}"),
                            "SK": serializer.serialize("METADATA"),
                        },
                        "UpdateExpression": "SET #status = :status, #sipk = :sipk",
                        "ConditionExpression": "#status = :expected_status",
                        "ExpressionAttributeNames": {
                            "#status": "Status",
                            "#sipk": "StatusIndexPK",
                        },
                        "ExpressionAttributeValues": {
                            ":status": serializer.serialize(
                                Asset_Status_Enum.RETURN_PENDING
                            ),
                            ":sipk": serializer.serialize(
                                f"STATUS#{Asset_Status_Enum.RETURN_PENDING.value}"
                            ),
                            ":expected_status": serializer.serialize(
                                Asset_Status_Enum.ASSIGNED
                            ),
                        },
                    }
                },
                {"Put": {"TableName": ASSETS_TABLE, "Item": return_item}},
                {"Put": {"TableName": ASSETS_TABLE, "Item": audit_item}},
            ]
        )

        # Backfill MaintenanceEntityIndex GSI fields — transact_write_items does not trigger streams
        table.update_item(
            Key={"PK": f"ASSET#{asset_id}", "SK": f"RETURN#{return_id}"},
            UpdateExpression="SET #met = :met, #mts = :mts, #mrt = :mrt",
            ExpressionAttributeNames={
                "#met": "MaintenanceEntityType",
                "#mts": "MaintenanceTimestamp",
                "#mrt": "MaintenanceRecordType",
            },
            ExpressionAttributeValues={
                ":met": "MAINTENANCE",
                ":mts": now,
                ":mrt": Maintenance_Record_Type_Enum.RETURN,
            },
        )

        response = InitiateReturnResponse(
            asset_id=asset_id,
            return_id=return_id,
            status=Asset_Status_Enum.RETURN_PENDING,
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
    except dynamodb_client.exceptions.TransactionCanceledException:
        return error("Asset status changed concurrently. Please retry.", 409)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
