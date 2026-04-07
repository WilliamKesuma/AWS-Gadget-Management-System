import os
import time
from datetime import datetime, timezone
from uuid import uuid4

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from pydantic import ValidationError

from utils import error, success, put_item
from utils.auth import require_group
from utils.enums import Scan_Status_Enum, User_Role_Enum
from utils.models import ScanJobModel, UploadSessionModel

from model import (
    GenerateUploadUrlsRequest,
    GenerateUploadUrlsResponse,
    PresignedUrlItem,
)

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]
ASSETS_BUCKET = os.environ["ASSETS_BUCKET"]
SCAN_WORKER_ARN = os.environ["SCAN_WORKER_ARN"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
s3_client = boto3.client("s3")
lambda_client = boto3.client("lambda")


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        require_group(event, User_Role_Enum.IT_ADMIN)

        body = json.loads(event.get("body") or "{}")
        request = GenerateUploadUrlsRequest(**body)

        upload_session_id = str(uuid4())
        scan_job_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Generate presigned URLs and collect S3 keys
        urls = []
        invoice_key = None
        gadget_photo_keys = []

        for file in request.files:
            file_type = file.type  # "invoice" or "gadget_photo"
            key = f"uploads/{upload_session_id}/{file_type}/{file.name}"

            presigned_url = s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": ASSETS_BUCKET,
                    "Key": key,
                    "ContentType": file.content_type,
                },
                ExpiresIn=900,  # 15 minutes
            )

            urls.append(
                PresignedUrlItem(
                    file_key=key, presigned_url=presigned_url, type=file_type
                )
            )

            if file_type == "invoice":
                invoice_key = key
            else:
                gadget_photo_keys.append(key)

        # Persist upload session
        session = UploadSessionModel(
            PK=f"SESSION#{upload_session_id}",
            SK="METADATA",
            UploadSessionID=upload_session_id,
            InvoiceS3Key=invoice_key,
            GadgetPhotoS3Keys=gadget_photo_keys,
            CreatedAt=now,
            TTL=int(time.time()) + 3600,
        )
        put_item(table, session.model_dump())

        # Create scan job in PROCESSING state
        scan_job = ScanJobModel(
            PK=f"SCAN#{scan_job_id}",
            SK="METADATA",
            ScanJobID=scan_job_id,
            UploadSessionID=upload_session_id,
            Status=Scan_Status_Enum.PROCESSING,
            CreatedAt=now,
        )
        put_item(table, scan_job.model_dump())

        # Fire ScanWorker asynchronously
        lambda_client.invoke(
            FunctionName=SCAN_WORKER_ARN,
            InvocationType="Event",
            Payload=json.dumps({"scan_job_id": scan_job_id}).encode(),
        )

        response = GenerateUploadUrlsResponse(
            upload_session_id=upload_session_id,
            scan_job_id=scan_job_id,
            urls=urls,
        )
        return success(response.model_dump())

    except ValidationError as e:
        return error(str(e), 400)
    except PermissionError as e:
        return error(str(e), 403)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
