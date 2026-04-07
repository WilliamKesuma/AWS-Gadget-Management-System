import os

import boto3
from aws_lambda_powertools import Logger, Tracer

from custom_exceptions import NotFoundException
from utils import error, get_item, success
from utils.auth import require_group
from utils.enums import User_Role_Enum
from utils.user_resolver import resolve_user_names, collect_user_ids

from model import AssetSpecs, GetDisposalDetailsResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        # Dual-group authorization: it-admin OR management
        try:
            actor_id = require_group(event, User_Role_Enum.IT_ADMIN)
        except PermissionError:
            try:
                actor_id = require_group(event, User_Role_Enum.MANAGEMENT)
            except PermissionError:
                raise PermissionError(
                    "Forbidden: IT Admin or Management access required"
                )

        asset_id = event["pathParameters"]["asset_id"]
        disposal_id = event["pathParameters"]["disposal_id"]

        # Validate asset exists
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        # Fetch disposal record directly by UUID
        item = get_item(
            table, {"PK": f"ASSET#{asset_id}", "SK": f"DISPOSAL#{disposal_id}"}
        )
        if not item:
            raise NotFoundException("Disposal record not found")

        # Map AssetSpecs nested object
        asset_specs = None
        if item.get("AssetSpecs"):
            specs = item["AssetSpecs"]
            asset_specs = AssetSpecs(
                brand=specs.get("Brand"),
                model=specs.get("Model"),
                serial_number=specs.get("SerialNumber"),
                product_description=specs.get("ProductDescription"),
                cost=specs.get("Cost"),
                purchase_date=specs.get("PurchaseDate"),
            )

        # Resolve user IDs to names
        user_ids = collect_user_ids(
            item["InitiatedBy"],
            item.get("ManagementReviewedBy"),
            item.get("CompletedBy"),
        )
        names = resolve_user_names(table, user_ids)

        disposal_status = (item.get("DisposalStatusIndexPK") or "").replace(
            "DISPOSAL_STATUS#", ""
        )

        response = GetDisposalDetailsResponse(
            asset_id=item["PK"].replace("ASSET#", ""),
            disposal_id=item.get("DisposalID", item["SK"].replace("DISPOSAL#", "")),
            status=disposal_status,
            disposal_reason=item["DisposalReason"],
            justification=item["Justification"],
            asset_specs=asset_specs,
            initiated_by=names.get(item["InitiatedBy"], item["InitiatedBy"]),
            initiated_by_id=item["InitiatedBy"],
            initiated_at=item["InitiatedAt"],
            management_reviewed_by=(
                names.get(item["ManagementReviewedBy"])
                if item.get("ManagementReviewedBy")
                else None
            ),
            management_reviewed_by_id=item.get("ManagementReviewedBy"),
            management_reviewed_at=item.get("ManagementReviewedAt"),
            management_approved_at=item.get("ManagementApprovedAt"),
            management_rejection_reason=item.get("ManagementRejectionReason"),
            management_remarks=item.get("ManagementRemarks"),
            disposal_date=item.get("DisposalDate"),
            data_wipe_confirmed=item.get("DataWipeConfirmed"),
            completed_by=(
                names.get(item["CompletedBy"]) if item.get("CompletedBy") else None
            ),
            completed_by_id=item.get("CompletedBy"),
            completed_at=item.get("CompletedAt"),
            is_locked=item.get("IsLocked", False),
            finance_notified_at=item.get("FinanceNotifiedAt"),
            finance_notification_sent=item.get("FinanceNotificationSent", False),
            finance_notification_status=item.get("FinanceNotificationStatus"),
        )

        return success(response.model_dump())

    except PermissionError as e:
        return error(str(e), 403)
    except NotFoundException as e:
        return error(str(e), 404)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
