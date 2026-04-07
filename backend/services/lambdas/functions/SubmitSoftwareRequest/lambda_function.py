import os
from datetime import datetime, timezone

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from pydantic import ValidationError

from custom_exceptions import NotFoundException, ConflictException
from utils import success, error, get_item
from utils.auth import require_group
from utils.enums import (
    Asset_Status_Enum,
    Email_Event_Type_Enum,
    Maintenance_Record_Type_Enum,
    Software_Status_Enum,
    User_Role_Enum,
)
from utils.models import AssetMetadataModel, AuditLogModel, SoftwareInstallationModel
from utils.id_generator import generate_domain_id
from utils.email_queue import send_email_event

from model import SubmitSoftwareRequestRequest, SubmitSoftwareRequestResponse

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
        actor_id = require_group(event, User_Role_Enum.EMPLOYEE)

        asset_id = event["pathParameters"]["asset_id"]

        body = json.loads(event.get("body") or "{}")
        request = SubmitSoftwareRequestRequest(**body)

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        asset = AssetMetadataModel(**asset_item)

        # Check asset is in ASSIGNED status
        if asset.Status != Asset_Status_Enum.ASSIGNED:
            raise ConflictException(
                "Software installation requests are only allowed for assets in ASSIGNED status"
            )

        # Query latest handover record to verify employee assignment
        handover_response = table.query(
            KeyConditionExpression=Key("PK").eq(f"ASSET#{asset_id}")
            & Key("SK").begins_with("HANDOVER#"),
            ScanIndexForward=False,
            Limit=1,
        )
        handover_items = handover_response.get("Items", [])

        if not handover_items or handover_items[0].get("EmployeeID") != actor_id:
            raise PermissionError("You are not assigned to this asset")

        # Duplicate detection: check for active requests with same software name, version, and vendor
        TERMINAL_STATUSES = {
            Software_Status_Enum.SOFTWARE_INSTALL_APPROVED,
            Software_Status_Enum.SOFTWARE_INSTALL_REJECTED,
        }

        existing_response = table.query(
            KeyConditionExpression=Key("PK").eq(f"ASSET#{asset_id}")
            & Key("SK").begins_with("SOFTWARE#"),
        )
        for item in existing_response.get("Items", []):
            if (
                item.get("SoftwareName", "").strip().lower()
                == request.software_name.strip().lower()
                and item.get("Version", "").strip().lower()
                == request.version.strip().lower()
                and item.get("Vendor", "").strip().lower()
                == request.vendor.strip().lower()
                and item.get("Status") not in TERMINAL_STATUSES
            ):
                raise ConflictException(
                    f"A request for {request.software_name} {request.version} by {request.vendor} "
                    f"is already pending review for this asset"
                )

        # Generate software request ID and timestamp
        software_request_id = generate_domain_id(table, "SOFTWARE")
        now = datetime.now(timezone.utc).isoformat()

        # Build SoftwareInstallationModel
        software_record = SoftwareInstallationModel(
            PK=f"ASSET#{asset_id}",
            SK=f"SOFTWARE#{software_request_id}",
            SoftwareRequestID=software_request_id,
            SoftwareName=request.software_name,
            Version=request.version,
            Vendor=request.vendor,
            Justification=request.justification,
            LicenseType=request.license_type,
            LicenseValidityPeriod=request.license_validity_period,
            DataAccessImpact=request.data_access_impact,
            Status=Software_Status_Enum.PENDING_REVIEW,
            RequestedBy=actor_id,
            CreatedAt=now,
            SoftwareStatusIndexPK=f"SOFTWARE_STATUS#{Software_Status_Enum.PENDING_REVIEW.value}",
            SoftwareStatusIndexSK=f"SOFTWARE#{software_request_id}",
        )

        # Build AuditLogModel
        audit_log = AuditLogModel(
            PK=f"ASSET#{asset_id}",
            SK=f"LOG#{now}#{actor_id}",
            ActorID=actor_id,
            Phase="SOFTWARE_INSTALL_REQUEST",
            PreviousStatus="",
            NewStatus=Software_Status_Enum.PENDING_REVIEW,
        )

        # Serialize items
        software_item = _serialize_item(software_record.model_dump())
        audit_item = _serialize_item(audit_log.model_dump())

        # TransactWriteItems: put Software_Installation_Record + put Audit_Log_Entry
        dynamodb_client.transact_write_items(
            TransactItems=[
                {"Put": {"TableName": ASSETS_TABLE, "Item": software_item}},
                {"Put": {"TableName": ASSETS_TABLE, "Item": audit_item}},
            ]
        )

        # Backfill MaintenanceEntityIndex GSI fields — transact_write_items does not trigger streams
        table.update_item(
            Key={"PK": f"ASSET#{asset_id}", "SK": f"SOFTWARE#{software_request_id}"},
            UpdateExpression="SET #met = :met, #mts = :mts, #mrt = :mrt",
            ExpressionAttributeNames={
                "#met": "MaintenanceEntityType",
                "#mts": "MaintenanceTimestamp",
                "#mrt": "MaintenanceRecordType",
            },
            ExpressionAttributeValues={
                ":met": "MAINTENANCE",
                ":mts": now,
                ":mrt": Maintenance_Record_Type_Enum.SOFTWARE_REQUEST,
            },
        )

        # Queue email notification to IT Admins via unified SQS pipeline
        send_email_event(
            Email_Event_Type_Enum.SOFTWARE_REQUEST_SUBMITTED,
            asset_id=asset_id,
            actor_name=handover_items[0]["EmployeeName"],
            actor_id=actor_id,
            software_name=request.software_name,
        )

        response = SubmitSoftwareRequestResponse(
            asset_id=asset_id,
            software_request_id=software_request_id,
            status=Software_Status_Enum.PENDING_REVIEW,
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
