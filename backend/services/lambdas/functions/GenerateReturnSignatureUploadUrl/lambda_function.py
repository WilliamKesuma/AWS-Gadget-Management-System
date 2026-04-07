"""
GenerateReturnSignatureUploadUrl — called by the Employee to get a presigned
PUT URL for uploading their digital signature for an asset return.
"""

import os

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from pydantic import ValidationError

from custom_exceptions import ConflictException, NotFoundException
from utils import error, get_item, success
from utils.auth import require_group
from utils.enums import Asset_Status_Enum, User_Role_Enum

from model import (
    GenerateReturnSignatureUploadUrlRequest,
    GenerateReturnSignatureUploadUrlResponse,
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
        actor_id = require_group(event, User_Role_Enum.EMPLOYEE)

        asset_id = event["pathParameters"]["asset_id"]
        return_id = event["pathParameters"]["return_id"]

        body = json.loads(event.get("body") or "{}")
        request = GenerateReturnSignatureUploadUrlRequest(**body)

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        if asset_item["Status"] != Asset_Status_Enum.RETURN_PENDING:
            raise ConflictException("Asset is not in RETURN_PENDING status")

        # Verify the caller is the assigned employee
        employee_index_pk = asset_item.get("EmployeeAssetIndexPK", "")
        assigned_employee_id = (
            employee_index_pk.replace("EMPLOYEE#", "") if employee_index_pk else None
        )
        if assigned_employee_id != actor_id:
            raise PermissionError("You are not assigned to this asset")

        # Fetch Return_Record
        return_item = get_item(
            table, {"PK": f"ASSET#{asset_id}", "SK": f"RETURN#{return_id}"}
        )
        if not return_item:
            raise NotFoundException("Return record not found")

        s3_key = f"returns/{asset_id}/{return_id}/user-signature/{request.file_name}"
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": ASSETS_BUCKET, "Key": s3_key, "ContentType": "image/png"},
            ExpiresIn=900,
        )

        response = GenerateReturnSignatureUploadUrlResponse(
            presigned_url=presigned_url,
            s3_key=s3_key,
            return_id=return_id,
            asset_id=asset_id,
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
