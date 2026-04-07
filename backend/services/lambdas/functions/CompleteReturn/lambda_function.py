"""
CompleteReturn — called by the Employee after uploading their signature.

Validates all evidence exists in S3, then transitions the asset to the
correct status based on the condition_assessment stored on the Return_Record.
"""

import os
from datetime import datetime, timezone

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.types import TypeSerializer
from pydantic import ValidationError

from custom_exceptions import ConflictException, NotFoundException
from utils import error, get_item, success, check_record_lock
from utils.auth import require_group
from utils.s3_helper import validate_and_clean_s3_key, validate_and_clean_s3_keys
from utils.enums import (
    Asset_Status_Enum,
    Issue_Category_Enum,
    Issue_Status_Enum,
    Return_Condition_Enum,
    Return_Status_Enum,
    User_Role_Enum,
)
from utils.models import AuditLogModel, IssueRepairModel
from utils.id_generator import generate_domain_id

from model import CompleteReturnRequest, CompleteReturnResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]
ASSETS_BUCKET = os.environ["ASSETS_BUCKET"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
dynamodb_client = boto3.client("dynamodb")
s3_client = boto3.client("s3")
serializer = TypeSerializer()

CONDITION_STATUS_MAP = {
    Return_Condition_Enum.GOOD: Asset_Status_Enum.IN_STOCK,
    Return_Condition_Enum.MINOR_DAMAGE: Asset_Status_Enum.DAMAGED,
    Return_Condition_Enum.MINOR_DAMAGE_REPAIR_REQUIRED: Asset_Status_Enum.ISSUE_REPORTED,
    Return_Condition_Enum.MAJOR_DAMAGE: Asset_Status_Enum.DISPOSAL_REVIEW,
}


def _serialize_item(item: dict) -> dict:
    return {k: serializer.serialize(v) for k, v in item.items() if v is not None}


def _validate_s3_evidence(
    return_record: dict, user_sig_key: str, asset_id: str, return_id: str
) -> None:
    """Validate all evidence files exist in S3, cleaning stale keys on miss."""
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
    validate_and_clean_s3_key(
        table,
        pk,
        sk,
        "UserSignatureS3Key",
        ASSETS_BUCKET,
        user_sig_key,
        "User signature",
    )


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id = require_group(event, User_Role_Enum.EMPLOYEE)

        asset_id = event["pathParameters"]["asset_id"]
        return_id = event["pathParameters"]["return_id"]

        body = json.loads(event.get("body") or "{}")
        request = CompleteReturnRequest(**body)

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        check_record_lock(asset_item)

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

        # Validate all evidence exists in S3
        _validate_s3_evidence(
            return_item, request.user_signature_s3_key, asset_id, return_id
        )

        # Map condition (stored at initiation) to target status
        condition = return_item.get("ConditionAssessment")
        target_status = CONDITION_STATUS_MAP.get(
            Return_Condition_Enum(condition), Asset_Status_Enum.IN_STOCK
        )

        now = datetime.now(timezone.utc).isoformat()

        audit_log = AuditLogModel(
            PK=f"ASSET#{asset_id}",
            SK=f"LOG#{now}#{actor_id}",
            ActorID=actor_id,
            Phase="ASSET_RETURN",
            PreviousStatus=Asset_Status_Enum.RETURN_PENDING,
            NewStatus=target_status,
            AdminDigitalSignature=return_item.get("AdminSignatureS3Key"),
            UserDigitalSignature=request.user_signature_s3_key,
            PhotoEvidenceURLs=return_item.get("ReturnPhotoS3Keys"),
        )
        audit_item = _serialize_item(audit_log.model_dump())

        # Auto-create issue record when condition requires repair (Phase 5 → Phase 4)
        issue_item = None
        if condition == Return_Condition_Enum.MINOR_DAMAGE_REPAIR_REQUIRED:
            issue_id = generate_domain_id(table, "ISSUE")
            issue_record = IssueRepairModel(
                PK=f"ASSET#{asset_id}",
                SK=f"ISSUE#{issue_id}",
                IssueID=issue_id,
                IssueDescription=f"Auto-generated from return {return_id}: asset returned with minor damage requiring repair. Remarks: {return_item.get('Remarks', 'N/A')}",
                Category=Issue_Category_Enum.HARDWARE,
                Status=Issue_Status_Enum.TROUBLESHOOTING,
                ActionPath=None,
                ReportedBy=actor_id,
                CreatedAt=now,
                IssueStatusIndexPK=f"ISSUE_STATUS#{Issue_Status_Enum.TROUBLESHOOTING.value}",
                IssueStatusIndexSK=f"ISSUE#{issue_id}",
            )
            issue_item = _serialize_item(issue_record.model_dump())

        # Asset update: set new status, clear employee index
        # If GOOD: also clear Condition and Remarks
        asset_update_expr = "SET #status = :status, #sipk = :sipk REMOVE #eaipk, #eaisk"
        asset_attr_names = {
            "#status": "Status",
            "#sipk": "StatusIndexPK",
            "#eaipk": "EmployeeAssetIndexPK",
            "#eaisk": "EmployeeAssetIndexSK",
        }
        asset_attr_values = {
            ":status": serializer.serialize(target_status),
            ":sipk": serializer.serialize(f"STATUS#{target_status.value}"),
        }

        if condition == Return_Condition_Enum.GOOD:
            asset_update_expr = (
                "SET #status = :status, #sipk = :sipk "
                "REMOVE #eaipk, #eaisk, #condition, #remarks"
            )
            asset_attr_names["#condition"] = "Condition"
            asset_attr_names["#remarks"] = "Remarks"

        # Return_Record update: store user signature key, completion metadata
        return_update_expr = (
            "SET #usig = :usig, #cat = :cat, #cb = :cb, #resolved = :resolved"
        )
        return_attr_names = {
            "#usig": "UserSignatureS3Key",
            "#cat": "CompletedAt",
            "#cb": "CompletedBy",
            "#resolved": "ResolvedStatus",
        }
        return_attr_values = {
            ":usig": serializer.serialize(request.user_signature_s3_key),
            ":cat": serializer.serialize(now),
            ":cb": serializer.serialize(actor_id),
            ":resolved": serializer.serialize(Return_Status_Enum.COMPLETED),
        }

        # Guard: status must still be RETURN_PENDING at write time
        asset_attr_names["#expected_status"] = "Status"
        asset_attr_values[":expected_status"] = serializer.serialize(
            Asset_Status_Enum.RETURN_PENDING
        )

        transact_items = [
            {
                "Update": {
                    "TableName": ASSETS_TABLE,
                    "Key": {
                        "PK": serializer.serialize(f"ASSET#{asset_id}"),
                        "SK": serializer.serialize("METADATA"),
                    },
                    "UpdateExpression": asset_update_expr,
                    "ConditionExpression": "#expected_status = :expected_status",
                    "ExpressionAttributeNames": asset_attr_names,
                    "ExpressionAttributeValues": asset_attr_values,
                }
            },
            {
                "Update": {
                    "TableName": ASSETS_TABLE,
                    "Key": {
                        "PK": serializer.serialize(f"ASSET#{asset_id}"),
                        "SK": serializer.serialize(f"RETURN#{return_id}"),
                    },
                    "UpdateExpression": return_update_expr,
                    "ExpressionAttributeNames": return_attr_names,
                    "ExpressionAttributeValues": return_attr_values,
                }
            },
            {"Put": {"TableName": ASSETS_TABLE, "Item": audit_item}},
        ]

        if issue_item:
            transact_items.append(
                {"Put": {"TableName": ASSETS_TABLE, "Item": issue_item}}
            )

        dynamodb_client.transact_write_items(TransactItems=transact_items)

        response = CompleteReturnResponse(
            asset_id=asset_id,
            new_status=target_status,
            completed_at=now,
        )
        return success(response.model_dump())

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
    except dynamodb_client.exceptions.TransactionCanceledException:
        return error("Asset status changed concurrently. Please retry.", 409)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
