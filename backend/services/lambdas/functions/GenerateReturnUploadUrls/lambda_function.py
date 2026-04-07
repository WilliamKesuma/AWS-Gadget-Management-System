import os

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from pydantic import ValidationError

from custom_exceptions import ConflictException, NotFoundException
from utils import error, get_item, success, update_item
from utils.auth import require_group
from utils.enums import Asset_Status_Enum, User_Role_Enum

from model import (
    GenerateReturnUploadUrlsRequest,
    GenerateReturnUploadUrlsResponse,
    ReturnPresignedUrlItem,
)

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
        actor_id = require_group(event, User_Role_Enum.IT_ADMIN)

        asset_id = event["pathParameters"]["asset_id"]
        return_id = event["pathParameters"]["return_id"]

        body = json.loads(event.get("body") or "{}")
        request = GenerateReturnUploadUrlsRequest(**body)

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        if asset_item["Status"] != Asset_Status_Enum.RETURN_PENDING:
            raise ConflictException(
                "Asset is not in RETURN_PENDING status. Upload URLs can only be generated for assets pending return"
            )

        # Fetch Return_Record
        return_item = get_item(
            table, {"PK": f"ASSET#{asset_id}", "SK": f"RETURN#{return_id}"}
        )
        if not return_item:
            raise NotFoundException("Return record not found")

        # Generate presigned PUT URLs — photos and admin-signature only
        urls: list[ReturnPresignedUrlItem] = []
        photo_s3_keys: list[str] = []
        admin_signature_s3_key = ""

        for file_item in request.files:
            s3_key = f"returns/{asset_id}/{return_id}/{file_item.type}/{file_item.name}"
            presigned_url = s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": ASSETS_BUCKET,
                    "Key": s3_key,
                    "ContentType": file_item.content_type,
                },
                ExpiresIn=900,
            )
            urls.append(
                ReturnPresignedUrlItem(
                    file_key=s3_key,
                    presigned_url=presigned_url,
                    type=file_item.type,
                    content_type=file_item.content_type,
                )
            )

            if file_item.type == "photo":
                photo_s3_keys.append(s3_key)
            elif file_item.type == "admin-signature":
                admin_signature_s3_key = s3_key

        # Store S3 keys on Return_Record — only update fields that were provided
        update_fields = {}
        if photo_s3_keys:
            update_fields["ReturnPhotoS3Keys"] = photo_s3_keys
        if admin_signature_s3_key:
            update_fields["AdminSignatureS3Key"] = admin_signature_s3_key

        if update_fields:
            update_item(
                table,
                {"PK": f"ASSET#{asset_id}", "SK": f"RETURN#{return_id}"},
                update_fields,
            )

        response = GenerateReturnUploadUrlsResponse(upload_urls=urls)
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
