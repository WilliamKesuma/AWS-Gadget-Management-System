import os
from datetime import datetime, timezone

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key
from pydantic import ValidationError

from custom_exceptions import ConflictException, NotFoundException
from utils import success, error, get_item
from utils.auth import require_group
from utils.enums import Asset_Status_Enum, User_Role_Enum
from utils.models import AssetMetadataModel

from model import GenerateSignatureUploadUrlResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]
ASSETS_BUCKET = os.environ["ASSETS_BUCKET"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
s3_client = boto3.client("s3")


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id = require_group(event, User_Role_Enum.EMPLOYEE)

        asset_id = event["pathParameters"]["asset_id"]

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        asset = AssetMetadataModel(**asset_item)

        # Check asset status is IN_STOCK
        if asset.Status != Asset_Status_Enum.IN_STOCK:
            raise ConflictException(
                "Asset is not in a state that allows signature upload"
            )

        # Query for Handover_Record(s) — latest first
        handover_results = table.query(
            KeyConditionExpression=Key("PK").eq(f"ASSET#{asset_id}")
            & Key("SK").begins_with("HANDOVER#"),
            ScanIndexForward=False,
        )["Items"]

        if not handover_results:
            raise NotFoundException("No assignment found for this asset")

        # Get the latest Handover_Record
        handover_record = handover_results[0]

        # Verify the caller is the assigned employee
        if actor_id != handover_record["EmployeeID"]:
            raise PermissionError("You are not assigned to this asset")

        # Check that the handover form has been generated
        if not handover_record.get("HandoverFormS3Key"):
            raise ConflictException(
                "Handover form must be generated before uploading a signature"
            )

        # Generate timestamp and S3 key
        now = datetime.now(timezone.utc).isoformat()
        s3_key = f"signatures/{actor_id}/{asset_id}/{now}.png"

        # Generate presigned PUT URL (15 min TTL)
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": ASSETS_BUCKET, "Key": s3_key, "ContentType": "image/png"},
            ExpiresIn=900,
        )

        resp = GenerateSignatureUploadUrlResponse(
            presigned_url=presigned_url,
            s3_key=s3_key,
            asset_id=asset_id,
        )
        return success(resp.model_dump())

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
