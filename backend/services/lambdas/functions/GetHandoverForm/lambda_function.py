import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key
from pydantic import ValidationError

from custom_exceptions import NotFoundException
from utils import success, error, get_item
from utils.enums import User_Role_Enum
from utils.models import AssetMetadataModel

from model import GetHandoverFormResponse

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
        # Extract caller claims from event
        claims = event["requestContext"]["authorizer"]["claims"]
        caller_id = claims["sub"]
        groups = claims.get("cognito:groups", "").split(",")

        # Determine caller role — must be it-admin or employee
        is_admin = User_Role_Enum.IT_ADMIN in groups
        is_employee = User_Role_Enum.EMPLOYEE in groups
        if not is_admin and not is_employee:
            raise PermissionError(
                "You must be an IT Admin or Employee to access this resource"
            )

        # Extract asset_id from path parameters
        asset_id = event["pathParameters"]["asset_id"]

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        # Validate asset model (ensures data integrity)
        AssetMetadataModel(**asset_item)

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

        # If caller is employee, verify they are assigned to this asset
        if is_employee and not is_admin:
            if caller_id != handover_record["EmployeeID"]:
                raise PermissionError("You are not assigned to this asset")

        # Check that the handover form has been generated
        handover_form_s3_key = handover_record.get("HandoverFormS3Key")
        if not handover_form_s3_key:
            raise NotFoundException("Handover form has not been generated yet")

        # Generate presigned GET URL (60 min TTL)
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": ASSETS_BUCKET, "Key": handover_form_s3_key},
            ExpiresIn=3600,
        )

        resp = GetHandoverFormResponse(
            asset_id=asset_id,
            presigned_url=presigned_url,
        )
        return success(resp.model_dump())

    except ValidationError as e:
        return error(str(e), 400)
    except PermissionError as e:
        return error(str(e), 403)
    except NotFoundException as e:
        return error(str(e), 404)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
