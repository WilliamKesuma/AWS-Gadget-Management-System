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
    GenerateIssueUploadUrlsRequest,
    GenerateIssueUploadUrlsResponse,
    IssuePresignedUrlItem,
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
        require_group(event, User_Role_Enum.EMPLOYEE)

        asset_id = event["pathParameters"]["asset_id"]
        issue_id = event["pathParameters"]["issue_id"]

        body = json.loads(event.get("body") or "{}")
        request = GenerateIssueUploadUrlsRequest(**body)

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        # Asset must be in ISSUE_REPORTED status (photos uploaded before triage)
        if asset_item["Status"] != Asset_Status_Enum.ISSUE_REPORTED:
            raise ConflictException(
                "Issue photos can only be uploaded when asset is in ISSUE_REPORTED status"
            )

        # Fetch issue record
        issue_item = get_item(
            table, {"PK": f"ASSET#{asset_id}", "SK": f"ISSUE#{issue_id}"}
        )
        if not issue_item:
            raise NotFoundException("Issue record not found")

        # Generate presigned URLs and collect S3 keys
        urls: list[IssuePresignedUrlItem] = []
        photo_s3_keys: list[str] = []

        for file_item in request.files:
            s3_key = f"issues/{asset_id}/{issue_id}/{file_item.type}/{file_item.name}"
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
                IssuePresignedUrlItem(
                    file_key=s3_key,
                    presigned_url=presigned_url,
                    type=file_item.type,
                    content_type=file_item.content_type,
                )
            )
            photo_s3_keys.append(s3_key)

        # Update Issue_Record with S3 keys
        update_item(
            table,
            {"PK": f"ASSET#{asset_id}", "SK": f"ISSUE#{issue_id}"},
            {"IssuePhotoS3Keys": photo_s3_keys},
        )

        response = GenerateIssueUploadUrlsResponse(upload_urls=urls)
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
