import os
from datetime import datetime, timezone

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key
from pydantic import ValidationError

from custom_exceptions import ConflictException, NotFoundException
from utils import error, get_item, put_item, success
from utils.auth import require_group
from utils.enums import Asset_Condition_Enum, Asset_Status_Enum, User_Role_Enum
from utils.models import (
    AssetMetadataModel,
    AuditLogModel,
    ScanJobModel,
    UploadSessionModel,
)
from utils.s3_helper import validate_s3_key, validate_s3_keys

from model import CreateAssetRequest, CreateAssetResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)


def _check_serial_unique(serial_number: str) -> None:
    response = table.query(
        IndexName="SerialNumberIndex",
        KeyConditionExpression=Key("SerialNumberIndexPK").eq(f"SERIAL#{serial_number}"),
        Limit=1,
    )
    if response.get("Count", 0) > 0:
        raise ConflictException("An asset with this serial number already exists")


def _increment_counter(category: str, year: int) -> int:
    response = table.update_item(
        Key={"PK": f"COUNTER#{category}#{year}", "SK": "METADATA"},
        UpdateExpression="ADD #count :inc",
        ExpressionAttributeNames={"#count": "Count"},
        ExpressionAttributeValues={":inc": 1},
        ReturnValues="UPDATED_NEW",
    )
    return int(response["Attributes"]["Count"])


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id = require_group(event, User_Role_Enum.IT_ADMIN)

        body = json.loads(event.get("body") or "{}")
        request = CreateAssetRequest(**body)

        # Validate category exists in DynamoDB via CategoryNameIndex GSI
        category_response = table.query(
            IndexName="CategoryNameIndex",
            KeyConditionExpression=Key("CategoryNameIndexPK").eq(
                f"CATEGORY_NAME#{request.category}"
            ),
            Limit=1,
        )
        if category_response.get("Count", 0) == 0:
            raise ValueError(f"Category '{request.category}' does not exist")

        # Serial number uniqueness check
        if request.serial_number:
            _check_serial_unique(request.serial_number)

        # Fetch S3 keys from scan job → upload session
        scan_item = get_item(
            table, {"PK": f"SCAN#{request.scan_job_id}", "SK": "METADATA"}
        )
        if not scan_item:
            raise NotFoundException("Scan job not found")
        scan_job = ScanJobModel(**scan_item)

        session_item = get_item(
            table, {"PK": f"SESSION#{scan_job.UploadSessionID}", "SK": "METADATA"}
        )
        if not session_item:
            raise NotFoundException("Upload session not found")
        session = UploadSessionModel(**session_item)

        # Validate uploaded files actually exist in S3 before creating the asset
        ASSETS_BUCKET = os.environ["ASSETS_BUCKET"]
        validate_s3_key(ASSETS_BUCKET, session.InvoiceS3Key, "Invoice")
        validate_s3_keys(ASSETS_BUCKET, session.GadgetPhotoS3Keys, "Gadget photos")

        # Generate structured asset ID
        year = datetime.now(timezone.utc).year
        count = _increment_counter(request.category, year)
        asset_id = f"{request.category}-{year}-{count:03d}"

        now = datetime.now(timezone.utc).isoformat()

        # Build asset record
        asset = AssetMetadataModel(
            PK=f"ASSET#{asset_id}",
            SK="METADATA",
            Category=request.category,
            Condition=Asset_Condition_Enum.GOOD,
            InvoiceNumber=request.invoice_number,
            Vendor=request.vendor,
            PurchaseDate=request.purchase_date,
            Brand=request.brand,
            Model=request.model_name,
            Cost=request.cost,
            SerialNumber=request.serial_number,
            ProductDescription=request.product_description,
            PaymentMethod=request.payment_method,
            Processor=request.processor,
            Storage=request.storage,
            OSVersion=request.os_version,
            Memory=request.memory,
            InvoiceS3Key=session.InvoiceS3Key,
            GadgetPhotoS3Keys=session.GadgetPhotoS3Keys,
            Status=Asset_Status_Enum.ASSET_PENDING_APPROVAL,
            CreatedAt=now,
            StatusIndexPK=f"STATUS#{Asset_Status_Enum.ASSET_PENDING_APPROVAL.value}",
            StatusIndexSK=f"ASSET#{asset_id}",
            SerialNumberIndexPK=(
                f"SERIAL#{request.serial_number}" if request.serial_number else None
            ),
            SerialNumberIndexSK="METADATA" if request.serial_number else None,
        )

        # Build audit log entry
        audit = AuditLogModel(
            PK=f"ASSET#{asset_id}",
            SK=f"LOG#{now}#{actor_id}",
            ActorID=actor_id,
            Phase="ASSET_CREATION",
            PreviousStatus="",
            NewStatus=Asset_Status_Enum.ASSET_PENDING_APPROVAL.value,
            PhotoEvidenceURLs=session.GadgetPhotoS3Keys,
        )

        put_item(table, asset.model_dump(exclude_none=True))
        put_item(table, audit.model_dump(exclude_none=True))

        return success(
            CreateAssetResponse(
                asset_id=asset_id,
                status=Asset_Status_Enum.ASSET_PENDING_APPROVAL.value,
            ).model_dump(),
            status_code=201,
        )

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
