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
    Maintenance_Record_Type_Enum,
    User_Role_Enum,
)
from utils.models import AuditLogModel, AssetSpecsModel, DisposalRecordModel
from utils.id_generator import generate_domain_id
from utils.email_queue import send_email_event

from model import InitiateDisposalRequest, InitiateDisposalResponse

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
        actor_id = require_group(event, User_Role_Enum.IT_ADMIN)

        asset_id = event["pathParameters"]["asset_id"]

        body = json.loads(event.get("body") or "{}")
        request = InitiateDisposalRequest(**body)

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        # Check record lock before any other validation
        check_record_lock(asset_item)

        # Validate asset is in DISPOSAL_REVIEW status
        current_status = asset_item["Status"]
        if current_status != Asset_Status_Enum.DISPOSAL_REVIEW:
            raise ConflictException(
                "Asset is not eligible for disposal. Only assets in DISPOSAL_REVIEW status can be initiated for disposal"
            )

        # Generate disposal ID and timestamp
        disposal_id = generate_domain_id(table, "DISPOSAL")
        now = datetime.now(timezone.utc).isoformat()

        # Capture asset specs snapshot
        asset_specs = AssetSpecsModel(
            Brand=asset_item.get("Brand"),
            Model=asset_item.get("Model"),
            SerialNumber=asset_item.get("SerialNumber"),
            ProductDescription=asset_item.get("ProductDescription"),
            Cost=asset_item.get("Cost"),
            PurchaseDate=asset_item.get("PurchaseDate"),
        )

        # Build DisposalRecordModel
        disposal_record = DisposalRecordModel(
            PK=f"ASSET#{asset_id}",
            SK=f"DISPOSAL#{disposal_id}",
            DisposalID=disposal_id,
            DisposalReason=request.disposal_reason,
            Justification=request.justification,
            AssetSpecs=asset_specs,
            InitiatedBy=actor_id,
            InitiatedAt=now,
            DisposalStatusIndexPK=f"DISPOSAL_STATUS#{Asset_Status_Enum.DISPOSAL_PENDING.value}",
            DisposalStatusIndexSK=f"DISPOSAL#{disposal_id}",
        )

        # Build AuditLogModel
        audit_log = AuditLogModel(
            PK=f"ASSET#{asset_id}",
            SK=f"LOG#{now}#{actor_id}",
            ActorID=actor_id,
            Phase="ASSET_DISPOSAL",
            PreviousStatus=current_status,
            NewStatus=Asset_Status_Enum.DISPOSAL_PENDING,
        )

        # Serialize items
        disposal_item = _serialize_item(disposal_record.model_dump())
        audit_item = _serialize_item(audit_log.model_dump())

        # TransactWriteItems: update Asset_Record status, put Disposal_Record, put Audit_Log
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
                        "ExpressionAttributeNames": {
                            "#status": "Status",
                            "#sipk": "StatusIndexPK",
                        },
                        "ExpressionAttributeValues": {
                            ":status": serializer.serialize(
                                Asset_Status_Enum.DISPOSAL_PENDING
                            ),
                            ":sipk": serializer.serialize(
                                f"STATUS#{Asset_Status_Enum.DISPOSAL_PENDING.value}"
                            ),
                        },
                    }
                },
                {"Put": {"TableName": ASSETS_TABLE, "Item": disposal_item}},
                {"Put": {"TableName": ASSETS_TABLE, "Item": audit_item}},
            ]
        )

        # Backfill MaintenanceEntityIndex GSI fields — transact_write_items does not trigger streams
        table.update_item(
            Key={"PK": f"ASSET#{asset_id}", "SK": f"DISPOSAL#{disposal_id}"},
            UpdateExpression="SET #met = :met, #mts = :mts, #mrt = :mrt",
            ExpressionAttributeNames={
                "#met": "MaintenanceEntityType",
                "#mts": "MaintenanceTimestamp",
                "#mrt": "MaintenanceRecordType",
            },
            ExpressionAttributeValues={
                ":met": "MAINTENANCE",
                ":mts": now,
                ":mrt": Maintenance_Record_Type_Enum.DISPOSAL,
            },
        )

        # Queue email notification to Management via unified SQS pipeline
        send_email_event(
            Email_Event_Type_Enum.DISPOSAL_PENDING,
            asset_id=asset_id,
            disposal_id=disposal_id,
            disposal_reason=request.disposal_reason,
            justification=request.justification,
            brand=asset_item.get("Brand"),
            model=asset_item.get("Model"),
            serial_number=asset_item.get("SerialNumber"),
        )

        response = InitiateDisposalResponse(
            asset_id=asset_id,
            disposal_id=disposal_id,
            status=Asset_Status_Enum.DISPOSAL_PENDING,
        )
        return success(response.model_dump(), status_code=201)

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
