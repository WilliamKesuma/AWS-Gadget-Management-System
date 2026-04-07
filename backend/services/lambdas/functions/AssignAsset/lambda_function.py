import base64
import os
import uuid
from datetime import datetime, timezone

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from dateutil.relativedelta import relativedelta
import weasyprint
from pydantic import ValidationError

from custom_exceptions import ConflictException, NotFoundException
from utils import success, error, get_item, check_record_lock
from utils.auth import require_group
from utils.enums import (
    Asset_Condition_Enum,
    Asset_Status_Enum,
    User_Role_Enum,
    User_Status_Enum,
)
from utils.models import (
    AssetMetadataModel,
    AuditLogModel,
    HandoverRecordModel,
    UserMetadataModel,
)

from model import AssignAssetRequest, AssignAssetResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]
ASSETS_BUCKET = os.environ["ASSETS_BUCKET"]
SES_SENDER_EMAIL = os.environ.get("SES_SENDER_EMAIL", "")
WARRANTY_MONTHS = 12

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
dynamodb_client = boto3.client("dynamodb")
s3_client = boto3.client("s3")
ses_client = boto3.client("ses")
serializer = TypeSerializer()


def _serialize_item(item: dict) -> dict:
    """Convert a Python dict to DynamoDB JSON format."""
    return {k: serializer.serialize(v) for k, v in item.items() if v is not None}


def calculate_warranty_validity(purchase_date_str: str) -> str:
    """Calculate warranty validity based on purchase date and WARRANTY_MONTHS."""
    try:
        purchase_date = datetime.fromisoformat(purchase_date_str).date()
        warranty_end = purchase_date + relativedelta(months=WARRANTY_MONTHS)
        warranty_end_fmt = warranty_end.strftime("%d %b %Y")
        if datetime.now(timezone.utc).date() <= warranty_end:
            return f"Valid (expires {warranty_end_fmt})"
        else:
            return f"Expired (ended {warranty_end_fmt})"
    except (ValueError, TypeError):
        return "Unknown"


def _fetch_photo_as_base64(s3_key: str) -> str | None:
    """Fetch a photo from S3 and return as base64-encoded string."""
    try:
        response = s3_client.get_object(Bucket=ASSETS_BUCKET, Key=s3_key)
        photo_bytes = response["Body"].read()
        return base64.b64encode(photo_bytes).decode("utf-8")
    except Exception:
        logger.warning(f"Failed to fetch photo from S3: {s3_key}")
        return None


def _build_photos_html(photo_s3_keys: list[str]) -> str:
    """Fetch photos from S3 and build HTML img tags."""
    if not photo_s3_keys:
        return ""

    photos_html = ""
    for s3_key in photo_s3_keys:
        b64 = _fetch_photo_as_base64(s3_key)
        if b64:
            content_type = "image/jpeg"
            if s3_key.lower().endswith(".png"):
                content_type = "image/png"
            photos_html += (
                f'<img src="data:{content_type};base64,{b64}" '
                f'style="max-width: 300px; max-height: 200px; margin: 5px; border: 1px solid #ddd;" />'
            )
    return photos_html


def _format_date(iso_str: str | None) -> str:
    """Format an ISO-8601 date string to 'DD MMM YYYY HH:mm'. Returns 'N/A' on failure."""
    if not iso_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%d %b %Y %H:%M")
    except (ValueError, TypeError):
        return iso_str


_CONDITION_LABELS: dict[str, str] = {
    Asset_Condition_Enum.GOOD: "Good",
    Asset_Condition_Enum.FAIR: "Fair",
    Asset_Condition_Enum.POOR: "Poor",
}


def _build_handover_html(
    asset: AssetMetadataModel,
    asset_id: str,
    employee_name: str,
    employee_email: str,
    assignment_date: str,
    admin_name: str,
    admin_id: str,
    warranty_validity: str,
    photos_html: str,
) -> str:
    """Build the HTML content for the handover form PDF."""
    photos_section = ""
    if photos_html:
        photos_section = f"""
        <h2>Asset Photos</h2>
        <div style="margin-top: 10px;">
            {photos_html}
        </div>
        """

    warranty_class = (
        "warranty-valid"
        if warranty_validity.startswith("Valid")
        else "warranty-expired"
    )

    return f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                color: #333;
            }}
            h1 {{
                text-align: center;
                color: #2c3e50;
                border-bottom: 2px solid #2c3e50;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #2c3e50;
                margin-top: 30px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 10px;
                text-align: left;
            }}
            th {{
                background-color: #f5f5f5;
                width: 35%;
                font-weight: bold;
            }}
            .warranty-valid {{
                color: #27ae60;
                font-weight: bold;
            }}
            .warranty-expired {{
                color: #e74c3c;
                font-weight: bold;
            }}
            .signature-area {{
                margin-top: 40px;
                padding: 20px;
                border: 1px solid #ccc;
                background-color: #fafafa;
            }}
            .signature-area p {{
                font-weight: bold;
                margin-bottom: 10px;
            }}
        </style>
    </head>
    <body>
        <h1>Asset Handover Form</h1>

        <h2>Asset Details</h2>
        <table>
            <tr><th>Asset ID</th><td>{asset_id}</td></tr>
            <tr><th>Brand</th><td>{asset.Brand or "N/A"}</td></tr>
            <tr><th>Model</th><td>{asset.Model or "N/A"}</td></tr>
            <tr><th>Serial Number</th><td>{asset.SerialNumber or "N/A"}</td></tr>
            <tr><th>Product Description</th><td>{asset.ProductDescription or "N/A"}</td></tr>
            <tr><th>Cost</th><td>{asset.Cost or "N/A"}</td></tr>
            <tr><th>Purchase Date</th><td>{_format_date(asset.PurchaseDate)}</td></tr>
            <tr><th>Vendor</th><td>{asset.Vendor or "N/A"}</td></tr>
            <tr><th>Condition</th><td>{_CONDITION_LABELS.get(asset.Condition.value, asset.Condition.value) if asset.Condition else "N/A"}</td></tr>
        </table>

        {photos_section}

        <h2>Assignment Details</h2>
        <table>
            <tr><th>Employee Name</th><td>{employee_name}</td></tr>
            <tr><th>Employee Email</th><td>{employee_email}</td></tr>
            <tr><th>Assignment Date</th><td>{_format_date(assignment_date)}</td></tr>
            <tr><th>Assigned By</th><td>{admin_name}</td></tr>
            <tr><th>Assigned By ID</th><td>{admin_id}</td></tr>
        </table>

        <h2>Warranty Status</h2>
        <table>
            <tr>
                <th>Warranty Validity</th>
                <td class="{warranty_class}">{warranty_validity}</td>
            </tr>
        </table>

        <div class="signature-area">
            <p>Employee Signature:</p>
            <div style="border: 1px solid #000; height: 100px; width: 300px;"></div>
            <p style="margin-top: 10px; font-size: 12px; color: #666;">
                By signing above, I acknowledge receipt of the above asset and confirm that it is in the described condition.
            </p>
        </div>
    </body>
    </html>
    """


def _send_assignment_email(employee_email: str, brand: str, model: str) -> None:
    """Send assignment notification email via SES. Failures are logged but not raised."""
    try:
        device_name = f"{brand or 'Unknown'} {model or 'Unknown'}"
        ses_client.send_email(
            Source=SES_SENDER_EMAIL,
            Destination={"ToAddresses": [employee_email]},
            Message={
                "Subject": {"Data": "Asset Assignment Notification"},
                "Body": {
                    "Text": {
                        "Data": (
                            f"You have been assigned a {device_name}. "
                            "Please log in to the system to review and accept the handover."
                        )
                    }
                },
            },
        )
    except Exception:
        logger.exception("Failed to send SES assignment email")


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id = require_group(event, User_Role_Enum.IT_ADMIN)

        asset_id = event["pathParameters"]["asset_id"]

        body = json.loads(event.get("body") or "{}")
        request = AssignAssetRequest(**body)

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        # Check record lock before any other validation
        check_record_lock(asset_item)

        asset = AssetMetadataModel(**asset_item)

        # Check if asset is ASSIGNED → 409 with employee name
        if asset.Status == Asset_Status_Enum.ASSIGNED:
            handover_results = table.query(
                KeyConditionExpression=Key("PK").eq(f"ASSET#{asset_id}")
                & Key("SK").begins_with("HANDOVER#")
            )["Items"]
            employee_name = "unknown"
            if handover_results:
                employee_name = handover_results[0].get("EmployeeName", "unknown")
            raise ConflictException(f"This Asset has been assigned to {employee_name}")

        # Check if asset is not IN_STOCK → 409
        if asset.Status != Asset_Status_Enum.IN_STOCK:
            raise ConflictException("Asset must be in IN_STOCK status to be assigned")

        # Asset is IN_STOCK → check for existing pending (unaccepted) Handover_Record
        handover_results = table.query(
            KeyConditionExpression=Key("PK").eq(f"ASSET#{asset_id}")
            & Key("SK").begins_with("HANDOVER#")
        )["Items"]
        pending_handovers = [h for h in handover_results if not h.get("AcceptedAt")]
        if pending_handovers:
            employee_name = pending_handovers[0].get("EmployeeName", "unknown")
            raise ConflictException(
                f"This Asset is in progress to be assigned to {employee_name}"
            )

        # Verify active employee exists
        user_item = get_item(
            table, {"PK": f"USER#{request.employee_id}", "SK": "METADATA"}
        )
        if not user_item or user_item.get("Status") != User_Status_Enum.ACTIVE:
            raise NotFoundException("Active employee not found")

        user = UserMetadataModel(**user_item)

        # Fetch IT Admin user record
        admin_item = get_item(table, {"PK": f"USER#{actor_id}", "SK": "METADATA"})
        admin = UserMetadataModel(**admin_item) if admin_item else None
        admin_name = admin.Fullname if admin else "IT Admin"

        # Fetch asset photos from S3 and convert to base64
        photo_s3_keys = asset_item.get("GadgetPhotoS3Keys", []) or []
        photos_html = _build_photos_html(photo_s3_keys)

        # Generate handover ID and timestamp
        handover_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Calculate warranty validity
        warranty_validity = calculate_warranty_validity(asset.PurchaseDate or "")

        # Build HTML and render PDF
        html_content = _build_handover_html(
            asset=asset,
            asset_id=asset_id,
            employee_name=user.Fullname,
            employee_email=user.Email,
            assignment_date=now,
            admin_name=admin_name,
            admin_id=actor_id,
            warranty_validity=warranty_validity,
            photos_html=photos_html,
        )

        pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()

        # Upload PDF to S3
        s3_key = f"handovers/{asset_id}/{handover_id}.pdf"
        s3_client.put_object(
            Bucket=ASSETS_BUCKET,
            Key=s3_key,
            Body=pdf_bytes,
            ContentType="application/pdf",
        )

        # Upload HTML source to S3 (used by AcceptHandover to re-render with signature)
        html_s3_key = f"handovers/{asset_id}/{handover_id}.html"
        s3_client.put_object(
            Bucket=ASSETS_BUCKET,
            Key=html_s3_key,
            Body=html_content.encode("utf-8"),
            ContentType="text/html",
        )

        # Build HandoverRecordModel with HandoverFormS3Key
        handover_record = HandoverRecordModel(
            PK=f"ASSET#{asset_id}",
            SK=f"HANDOVER#{handover_id}",
            HandoverID=handover_id,
            EmployeeID=request.employee_id,
            EmployeeName=user.Fullname,
            EmployeeEmail=user.Email,
            AssignedByID=actor_id,
            AssignmentDate=now,
            Notes=request.notes,
            HandoverFormS3Key=s3_key,
            HandoverFormHtmlS3Key=html_s3_key,
        )

        # Build AuditLogModel — status stays IN_STOCK until employee accepts
        audit_log = AuditLogModel(
            PK=f"ASSET#{asset_id}",
            SK=f"LOG#{now}#{actor_id}",
            ActorID=actor_id,
            Phase="ASSET_ASSIGNMENT",
            PreviousStatus=Asset_Status_Enum.IN_STOCK,
            NewStatus=Asset_Status_Enum.IN_STOCK,
        )

        # Serialize items
        handover_item = _serialize_item(handover_record.model_dump())
        audit_item = _serialize_item(audit_log.model_dump())

        # TransactWriteItems: put Handover_Record, update Asset GSI keys, put AuditLog
        # Guard: status must still be IN_STOCK at write time
        dynamodb_client.transact_write_items(
            TransactItems=[
                {"Put": {"TableName": ASSETS_TABLE, "Item": handover_item}},
                {
                    "Update": {
                        "TableName": ASSETS_TABLE,
                        "Key": {
                            "PK": serializer.serialize(f"ASSET#{asset_id}"),
                            "SK": serializer.serialize("METADATA"),
                        },
                        "UpdateExpression": "SET #eapk = :eapk, #eask = :eask",
                        "ConditionExpression": "#status = :expected_status",
                        "ExpressionAttributeNames": {
                            "#eapk": "EmployeeAssetIndexPK",
                            "#eask": "EmployeeAssetIndexSK",
                            "#status": "Status",
                        },
                        "ExpressionAttributeValues": {
                            ":eapk": serializer.serialize(
                                f"EMPLOYEE#{request.employee_id}"
                            ),
                            ":eask": serializer.serialize(f"ASSET#{now}"),
                            ":expected_status": serializer.serialize(
                                Asset_Status_Enum.IN_STOCK
                            ),
                        },
                    }
                },
                {"Put": {"TableName": ASSETS_TABLE, "Item": audit_item}},
            ]
        )

        # Send SES email (non-critical — log failures but don't fail the request)
        _send_assignment_email(user.Email, asset.Brand, asset.Model)

        # Generate presigned GET URL (60 min TTL)
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": ASSETS_BUCKET, "Key": s3_key},
            ExpiresIn=3600,
        )

        response = AssignAssetResponse(
            asset_id=asset_id,
            employee_id=request.employee_id,
            assignment_date=now,
            status=Asset_Status_Enum.IN_STOCK,
            presigned_url=presigned_url,
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
    except dynamodb_client.exceptions.TransactionCanceledException:
        return error("Asset status changed concurrently. Please retry.", 409)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
