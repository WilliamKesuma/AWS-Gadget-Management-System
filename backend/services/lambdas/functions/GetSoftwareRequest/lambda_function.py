import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key

from custom_exceptions import NotFoundException
from utils import success, error, get_item
from utils.enums import User_Role_Enum
from utils.models import AssetMetadataModel
from utils.user_resolver import resolve_user_names, collect_user_ids

from model import GetSoftwareRequestResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)


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
        software_request_id = event["pathParameters"]["software_request_id"]

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        # Fetch software installation record
        software_item = get_item(
            table, {"PK": f"ASSET#{asset_id}", "SK": f"SOFTWARE#{software_request_id}"}
        )
        if not software_item:
            raise NotFoundException("Software installation request not found")

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

        # Resolve user IDs to names
        user_ids = collect_user_ids(
            software_item["RequestedBy"],
            software_item.get("ReviewedBy"),
            software_item.get("ManagementReviewedBy"),
        )
        names = resolve_user_names(table, user_ids)

        # Map DynamoDB item to response model
        response = GetSoftwareRequestResponse(
            asset_id=software_item["PK"].replace("ASSET#", ""),
            software_request_id=software_item.get(
                "SoftwareRequestID", software_item["SK"].replace("SOFTWARE#", "")
            ),
            software_name=software_item["SoftwareName"],
            version=software_item["Version"],
            vendor=software_item["Vendor"],
            justification=software_item["Justification"],
            license_type=software_item["LicenseType"],
            license_validity_period=software_item["LicenseValidityPeriod"],
            data_access_impact=software_item["DataAccessImpact"],
            status=software_item["Status"],
            risk_level=software_item.get("RiskLevel"),
            requested_by=names.get(
                software_item["RequestedBy"], software_item["RequestedBy"]
            ),
            requested_by_id=software_item["RequestedBy"],
            reviewed_by=(
                names.get(software_item["ReviewedBy"])
                if software_item.get("ReviewedBy")
                else None
            ),
            reviewed_by_id=software_item.get("ReviewedBy"),
            reviewed_at=software_item.get("ReviewedAt"),
            rejection_reason=software_item.get("RejectionReason"),
            management_reviewed_by=(
                names.get(software_item["ManagementReviewedBy"])
                if software_item.get("ManagementReviewedBy")
                else None
            ),
            management_reviewed_by_id=software_item.get("ManagementReviewedBy"),
            management_reviewed_at=software_item.get("ManagementReviewedAt"),
            management_rejection_reason=software_item.get("ManagementRejectionReason"),
            management_remarks=software_item.get("ManagementRemarks"),
            created_at=software_item["CreatedAt"],
            installation_timestamp=software_item.get("InstallationTimestamp"),
        )

        return success(response.model_dump())

    except PermissionError as e:
        return error(str(e), 403)
    except NotFoundException as e:
        return error(str(e), 404)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
