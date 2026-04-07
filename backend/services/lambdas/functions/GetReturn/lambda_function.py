import os

import boto3
from aws_lambda_powertools import Logger, Tracer

from custom_exceptions import NotFoundException
from utils import success, error, get_item
from utils.auth import require_roles
from utils.enums import User_Role_Enum
from utils.user_resolver import resolve_user_names, collect_user_ids

from model import GetReturnResponse

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
        actor_id, actor_role = require_roles(
            event, [User_Role_Enum.IT_ADMIN, User_Role_Enum.EMPLOYEE]
        )

        asset_id = event["pathParameters"]["asset_id"]
        return_id = event["pathParameters"]["return_id"]

        # Fetch return record
        return_item = get_item(
            table, {"PK": f"ASSET#{asset_id}", "SK": f"RETURN#{return_id}"}
        )
        if not return_item:
            raise NotFoundException("Return record not found")

        # Fetch asset metadata for current status
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        # Employees can only view returns for assets assigned to them
        if actor_role == User_Role_Enum.EMPLOYEE:
            employee_index_pk = asset_item.get("EmployeeAssetIndexPK", "")
            assigned_employee_id = (
                employee_index_pk.replace("EMPLOYEE#", "")
                if employee_index_pk
                else None
            )
            # Also allow if they were the one who completed the return
            completed_by = return_item.get("CompletedBy")
            if assigned_employee_id != actor_id and completed_by != actor_id:
                raise PermissionError("You do not have access to this return record")

        # Generate presigned GET URLs for evidence
        return_photo_urls = None
        admin_signature_url = None
        user_signature_url = None

        photo_keys = return_item.get("ReturnPhotoS3Keys")
        if photo_keys:
            return_photo_urls = [
                s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": ASSETS_BUCKET, "Key": key},
                    ExpiresIn=900,
                )
                for key in photo_keys
            ]

        admin_sig_key = return_item.get("AdminSignatureS3Key")
        if admin_sig_key:
            admin_signature_url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": ASSETS_BUCKET, "Key": admin_sig_key},
                ExpiresIn=900,
            )

        user_sig_key = return_item.get("UserSignatureS3Key")
        if user_sig_key:
            user_signature_url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": ASSETS_BUCKET, "Key": user_sig_key},
                ExpiresIn=900,
            )

        # Resolve user IDs to names
        user_ids = collect_user_ids(
            return_item["InitiatedBy"],
            return_item.get("CompletedBy"),
        )
        names = resolve_user_names(table, user_ids)

        response = GetReturnResponse(
            asset_id=return_item["PK"].replace("ASSET#", ""),
            return_id=return_item.get(
                "ReturnID", return_item["SK"].replace("RETURN#", "")
            ),
            return_trigger=return_item["ReturnTrigger"],
            initiated_by=names.get(
                return_item["InitiatedBy"], return_item["InitiatedBy"]
            ),
            initiated_by_id=return_item["InitiatedBy"],
            initiated_at=return_item["InitiatedAt"],
            condition_assessment=return_item["ConditionAssessment"],
            remarks=return_item["Remarks"],
            reset_status=return_item["ResetStatus"],
            serial_number=return_item.get("SerialNumber"),
            model=return_item.get("Model"),
            return_photo_urls=return_photo_urls,
            admin_signature_url=admin_signature_url,
            user_signature_url=user_signature_url,
            completed_at=return_item.get("CompletedAt"),
            completed_by=(
                names.get(return_item["CompletedBy"])
                if return_item.get("CompletedBy")
                else None
            ),
            completed_by_id=return_item.get("CompletedBy"),
            resolved_status=return_item.get("ResolvedStatus"),
            asset_status=asset_item["Status"],
        )

        return success(response.model_dump())

    except PermissionError as e:
        return error(str(e), 403)
    except NotFoundException as e:
        return error(str(e), 404)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
