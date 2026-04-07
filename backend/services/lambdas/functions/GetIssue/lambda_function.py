import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key

from custom_exceptions import NotFoundException
from utils import success, error, get_item
from utils.enums import User_Role_Enum
from utils.s3_helper import validate_and_clean_s3_keys
from utils.user_resolver import resolve_user_names, collect_user_ids

from model import GetIssueResponse

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
        # Extract caller claims and check authorization
        claims = event["requestContext"]["authorizer"]["claims"]
        groups = claims.get("cognito:groups", "").split(",")
        actor_id = claims["sub"]

        is_it_admin = User_Role_Enum.IT_ADMIN in groups
        is_management = User_Role_Enum.MANAGEMENT in groups
        is_employee = User_Role_Enum.EMPLOYEE in groups

        if not is_it_admin and not is_management and not is_employee:
            raise PermissionError("Insufficient permissions")

        asset_id = event["pathParameters"]["asset_id"]
        issue_id = event["pathParameters"]["issue_id"]

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        # If employee, verify assignment via latest handover record
        if is_employee:
            handover_response = table.query(
                KeyConditionExpression=Key("PK").eq(f"ASSET#{asset_id}")
                & Key("SK").begins_with("HANDOVER#"),
                ScanIndexForward=False,
                Limit=1,
            )
            handover_items = handover_response.get("Items", [])

            if not handover_items or handover_items[0].get("EmployeeID") != actor_id:
                raise PermissionError("You are not assigned to this asset")

        # Fetch issue record
        issue_item = get_item(
            table, {"PK": f"ASSET#{asset_id}", "SK": f"ISSUE#{issue_id}"}
        )
        if not issue_item:
            raise NotFoundException("Issue record not found")

        # Employees can only view their own issues
        if is_employee and not is_it_admin and not is_management:
            if issue_item.get("ReportedBy") != actor_id:
                raise PermissionError("You do not have access to this issue")

        # Resolve user IDs to names
        user_ids = collect_user_ids(
            issue_item["ReportedBy"],
            issue_item.get("ResolvedBy"),
            issue_item.get("ManagementReviewedBy"),
        )
        names = resolve_user_names(table, user_ids)

        # Generate presigned URLs for issue photos
        issue_photo_urls = None
        photo_keys = issue_item.get("IssuePhotoS3Keys")
        if photo_keys:
            validate_and_clean_s3_keys(
                table,
                f"ASSET#{asset_id}",
                f"ISSUE#{issue_id}",
                "IssuePhotoS3Keys",
                ASSETS_BUCKET,
                photo_keys,
                "Issue photos",
            )
            issue_photo_urls = [
                s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": ASSETS_BUCKET, "Key": key},
                    ExpiresIn=3600,
                )
                for key in photo_keys
            ]

        # Map DynamoDB item to response model
        response = GetIssueResponse(
            asset_id=issue_item["PK"].replace("ASSET#", ""),
            issue_id=issue_item.get("IssueID", issue_item["SK"].replace("ISSUE#", "")),
            issue_description=issue_item["IssueDescription"],
            category=issue_item["Category"],
            status=issue_item["Status"],
            action_path=issue_item.get("ActionPath"),
            reported_by=names.get(issue_item["ReportedBy"], issue_item["ReportedBy"]),
            reported_by_id=issue_item["ReportedBy"],
            created_at=issue_item["CreatedAt"],
            issue_photo_urls=issue_photo_urls,
            resolved_by=(
                names.get(issue_item["ResolvedBy"])
                if issue_item.get("ResolvedBy")
                else None
            ),
            resolved_by_id=issue_item.get("ResolvedBy"),
            resolved_at=issue_item.get("ResolvedAt"),
            repair_notes=issue_item.get("RepairNotes"),
            warranty_notes=issue_item.get("WarrantyNotes"),
            warranty_sent_at=issue_item.get("WarrantySentAt"),
            replacement_justification=issue_item.get("ReplacementJustification"),
            management_reviewed_by=(
                names.get(issue_item["ManagementReviewedBy"])
                if issue_item.get("ManagementReviewedBy")
                else None
            ),
            management_reviewed_by_id=issue_item.get("ManagementReviewedBy"),
            management_reviewed_at=issue_item.get("ManagementReviewedAt"),
            management_rejection_reason=issue_item.get("ManagementRejectionReason"),
            management_remarks=issue_item.get("ManagementRemarks"),
            completed_at=issue_item.get("CompletedAt"),
            completion_notes=issue_item.get("CompletionNotes"),
        )

        return success(response.model_dump())

    except ValueError as e:
        return error(str(e), 400)
    except PermissionError as e:
        return error(str(e), 403)
    except NotFoundException as e:
        return error(str(e), 404)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
