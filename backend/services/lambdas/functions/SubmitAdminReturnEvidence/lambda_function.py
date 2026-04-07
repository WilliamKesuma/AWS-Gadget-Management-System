"""
SubmitAdminReturnEvidence — called by IT Admin after all admin-side files
(photos + admin signature) have been uploaded to S3.

Validates that the evidence exists in S3, then queues an email notification
to the assigned employee asking them to review and sign the return form.
"""

import os

import boto3
from aws_lambda_powertools import Logger, Tracer

from custom_exceptions import ConflictException, NotFoundException
from utils import error, get_item, success
from utils.auth import require_group
from utils.enums import Asset_Status_Enum, Email_Event_Type_Enum, User_Role_Enum
from utils.models import UserMetadataModel
from utils.s3_helper import validate_and_clean_s3_key, validate_and_clean_s3_keys
from utils.email_queue import send_email_event

from model import SubmitAdminReturnEvidenceResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]
ASSETS_BUCKET = os.environ["ASSETS_BUCKET"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
s3_client = boto3.client("s3")


def _validate_s3_evidence(return_record: dict, asset_id: str, return_id: str) -> None:
    """Validate that admin-side evidence files exist in S3, cleaning stale keys on miss."""
    pk, sk = f"ASSET#{asset_id}", f"RETURN#{return_id}"
    validate_and_clean_s3_keys(
        table,
        pk,
        sk,
        "ReturnPhotoS3Keys",
        ASSETS_BUCKET,
        return_record.get("ReturnPhotoS3Keys"),
        "Return photo evidence",
    )
    validate_and_clean_s3_key(
        table,
        pk,
        sk,
        "AdminSignatureS3Key",
        ASSETS_BUCKET,
        return_record.get("AdminSignatureS3Key"),
        "Admin signature",
    )


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id = require_group(event, User_Role_Enum.IT_ADMIN)

        asset_id = event["pathParameters"]["asset_id"]
        return_id = event["pathParameters"]["return_id"]

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        if asset_item["Status"] != Asset_Status_Enum.RETURN_PENDING:
            raise ConflictException("Asset is not in RETURN_PENDING status")

        # Fetch Return_Record
        return_item = get_item(
            table, {"PK": f"ASSET#{asset_id}", "SK": f"RETURN#{return_id}"}
        )
        if not return_item:
            raise NotFoundException("Return record not found")

        # Validate evidence exists in S3
        _validate_s3_evidence(return_item, asset_id, return_id)

        # Resolve assigned employee from EmployeeAssetIndexPK
        # Format: EMPLOYEE#<EmployeeID>
        employee_index_pk = asset_item.get("EmployeeAssetIndexPK", "")
        employee_id = (
            employee_index_pk.replace("EMPLOYEE#", "") if employee_index_pk else None
        )

        if employee_id:
            employee_item = get_item(
                table, {"PK": f"USER#{employee_id}", "SK": "METADATA"}
            )
            if employee_item:
                user = UserMetadataModel(**employee_item)
                send_email_event(
                    Email_Event_Type_Enum.RETURN_EVIDENCE_SUBMITTED,
                    asset_id=asset_id,
                    employee_email=user.Email,
                    employee_name=user.Fullname,
                    asset_model=return_item.get("Model") or asset_item.get("Model", ""),
                    asset_serial=return_item.get("SerialNumber")
                    or asset_item.get("SerialNumber", ""),
                )

        response = SubmitAdminReturnEvidenceResponse(
            asset_id=asset_id,
            return_id=return_id,
            message="Evidence submitted. Employee has been notified to provide their signature.",
        )
        return success(response.model_dump())

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
