import os

import boto3
from aws_lambda_powertools import Logger, Tracer

from custom_exceptions import NotFoundException
from utils import error, get_item, success
from utils.auth import get_caller_info
from utils.enums import User_Role_Enum

from model import AssigneeInfo, GetAssetResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]
ASSETS_BUCKET = os.environ["ASSETS_BUCKET"]
PRESIGNED_URL_EXPIRY = 3600  # 1 hour

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
s3_client = boto3.client("s3")


def _generate_presigned_url(key: str) -> str:
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": ASSETS_BUCKET, "Key": key},
        ExpiresIn=PRESIGNED_URL_EXPIRY,
    )


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id, groups = get_caller_info(event)

        # Allow it-admin, management, or employee
        allowed_roles = {
            User_Role_Enum.IT_ADMIN,
            User_Role_Enum.MANAGEMENT,
            User_Role_Enum.EMPLOYEE,
        }
        if not allowed_roles.intersection(groups):
            raise PermissionError(
                "Forbidden: IT Admin, Management, or Employee access required"
            )

        is_employee = (
            User_Role_Enum.EMPLOYEE in groups
            and User_Role_Enum.IT_ADMIN not in groups
            and User_Role_Enum.MANAGEMENT not in groups
        )

        asset_id = event["pathParameters"]["asset_id"]

        item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not item:
            raise NotFoundException("Asset not found")

        # Employees can only view assets assigned (or pending assignment) to them
        if is_employee:
            assigned_to = item.get("EmployeeAssetIndexPK", "")
            if assigned_to != f"EMPLOYEE#{actor_id}":
                raise PermissionError("You are not assigned to this asset")

        # Look up assignee info if asset is assigned to an employee
        assignee = None
        employee_pk = item.get("EmployeeAssetIndexPK")
        if employee_pk:
            employee_id = employee_pk.replace("EMPLOYEE#", "")
            user_item = get_item(table, {"PK": f"USER#{employee_id}", "SK": "METADATA"})
            if user_item:
                assignee = AssigneeInfo(
                    user_id=employee_id,
                    fullname=user_item.get("Fullname", ""),
                    role=user_item.get("Role", ""),
                )

        # Generate presigned GET URLs for evidence files
        invoice_url = None
        if item.get("InvoiceS3Key"):
            invoice_url = _generate_presigned_url(item["InvoiceS3Key"])

        gadget_photo_urls = None
        if item.get("GadgetPhotoS3Keys"):
            gadget_photo_urls = [
                _generate_presigned_url(key) for key in item["GadgetPhotoS3Keys"]
            ]

        response = GetAssetResponse(
            asset_id=item["PK"].replace("ASSET#", ""),
            invoice_number=item.get("InvoiceNumber"),
            vendor=item.get("Vendor"),
            purchase_date=item.get("PurchaseDate"),
            serial_number=item.get("SerialNumber"),
            brand=item.get("Brand"),
            model=item.get("Model"),
            product_description=item.get("ProductDescription"),
            cost=float(item["Cost"]) if item.get("Cost") is not None else None,
            payment_method=item.get("PaymentMethod"),
            processor=item.get("Processor"),
            storage=item.get("Storage"),
            os_version=item.get("OSVersion"),
            memory=item.get("Memory"),
            invoice_url=invoice_url,
            gadget_photo_urls=gadget_photo_urls,
            status=item["Status"],
            category=item.get("Category"),
            condition=item.get("Condition"),
            remarks=item.get("Remarks"),
            rejection_reason=item.get("RejectionReason"),
            created_at=item.get("CreatedAt"),
            assigned_date=(
                item["EmployeeAssetIndexSK"].replace("ASSET#", "")
                if item.get("EmployeeAssetIndexSK")
                else None
            ),
            assignee=assignee,
        )

        return success(response.model_dump())

    except PermissionError as e:
        return error(str(e), 403)
    except NotFoundException as e:
        return error(str(e), 404)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
