import base64
import os
from datetime import datetime, timezone

import boto3
import simplejson as json
import weasyprint
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from pydantic import ValidationError

from custom_exceptions import ConflictException, NotFoundException
from utils import error, get_item, success, check_record_lock
from utils.auth import require_group
from utils.enums import Asset_Status_Enum, User_Role_Enum
from utils.models import AuditLogModel
from utils.s3_helper import validate_s3_key

from model import AcceptHandoverRequest, AcceptHandoverResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]
ASSETS_BUCKET = os.environ["ASSETS_BUCKET"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
dynamodb_client = boto3.client("dynamodb")
s3_client = boto3.client("s3")
serializer = TypeSerializer()


def _serialize_item(item: dict) -> dict:
    """Convert a Python dict to DynamoDB JSON format."""
    return {k: serializer.serialize(v) for k, v in item.items() if v is not None}


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id = require_group(event, User_Role_Enum.EMPLOYEE)

        asset_id = event["pathParameters"]["asset_id"]

        body = json.loads(event.get("body") or "{}")
        request = AcceptHandoverRequest(**body)

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        # Check record lock before any other validation
        check_record_lock(asset_item)

        # Check asset status is IN_STOCK
        if asset_item["Status"] != Asset_Status_Enum.IN_STOCK:
            raise ConflictException(
                "Asset is not in a state that allows handover acceptance"
            )

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

        # Verify the caller is the assigned employee
        if actor_id != handover_record["EmployeeID"]:
            raise PermissionError("You are not assigned to this asset")

        # Check that the handover form has been generated
        if not handover_record.get("HandoverFormS3Key"):
            raise ConflictException("Handover form must be generated before acceptance")

        # Generate timestamp
        now = datetime.now(timezone.utc).isoformat()

        # Verify signature exists in S3
        validate_s3_key(ASSETS_BUCKET, request.signature_s3_key, "Signature image")

        # Download existing PDF from S3
        pdf_response = s3_client.get_object(
            Bucket=ASSETS_BUCKET, Key=handover_record["HandoverFormS3Key"]
        )
        pdf_bytes = pdf_response["Body"].read()

        # Download signature image from S3
        sig_response = s3_client.get_object(
            Bucket=ASSETS_BUCKET, Key=request.signature_s3_key
        )
        sig_bytes = sig_response["Body"].read()

        sig_b64 = base64.b64encode(sig_bytes).decode("utf-8")

        # Fetch the stored HTML source and re-render with the signature injected
        # directly into the signature box — avoids fixed-position overlay issues
        html_s3_key = handover_record.get("HandoverFormHtmlS3Key")
        if not html_s3_key:
            return error(
                "Handover form HTML source not found; cannot embed signature", 500
            )

        html_response = s3_client.get_object(Bucket=ASSETS_BUCKET, Key=html_s3_key)
        original_html = html_response["Body"].read().decode("utf-8")

        # Replace the empty signature box with the actual signature image
        signed_html = original_html.replace(
            '<div style="border: 1px solid #000; height: 100px; width: 300px;"></div>',
            f'<img src="data:image/png;base64,{sig_b64}" style="max-width:300px;max-height:100px;display:block;" />',
        )
        signed_pdf_bytes = weasyprint.HTML(string=signed_html).write_pdf()

        # Upload signed PDF to S3
        signed_s3_key = f"handovers/{asset_id}/{now}-signed.pdf"
        s3_client.put_object(
            Bucket=ASSETS_BUCKET,
            Key=signed_s3_key,
            Body=signed_pdf_bytes,
            ContentType="application/pdf",
        )

        # Generate presigned GET URL for signed PDF (60 min TTL)
        signed_form_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": ASSETS_BUCKET, "Key": signed_s3_key},
            ExpiresIn=3600,
        )

        # Build audit log
        audit_log = AuditLogModel(
            PK=f"ASSET#{asset_id}",
            SK=f"LOG#{now}#{actor_id}",
            ActorID=actor_id,
            Phase="ASSET_HANDOVER",
            PreviousStatus=Asset_Status_Enum.IN_STOCK,
            NewStatus=Asset_Status_Enum.ASSIGNED,
            UserDigitalSignature=request.signature_s3_key,
        )
        audit_item = _serialize_item(audit_log.model_dump())

        # TransactWriteItems: update Handover_Record, update Asset status, put AuditLog
        dynamodb_client.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "TableName": ASSETS_TABLE,
                        "Key": {
                            "PK": serializer.serialize(handover_record["PK"]),
                            "SK": serializer.serialize(handover_record["SK"]),
                        },
                        "UpdateExpression": "SET SignatureS3Key = :sig, SignedFormS3Key = :signed, AcceptedAt = :at",
                        "ExpressionAttributeValues": {
                            ":sig": serializer.serialize(request.signature_s3_key),
                            ":signed": serializer.serialize(signed_s3_key),
                            ":at": serializer.serialize(now),
                        },
                    }
                },
                {
                    "Update": {
                        "TableName": ASSETS_TABLE,
                        "Key": {
                            "PK": serializer.serialize(f"ASSET#{asset_id}"),
                            "SK": serializer.serialize("METADATA"),
                        },
                        "UpdateExpression": "SET #status = :status, #sipk = :sipk",
                        "ConditionExpression": "#status = :expected_status",
                        "ExpressionAttributeNames": {
                            "#status": "Status",
                            "#sipk": "StatusIndexPK",
                        },
                        "ExpressionAttributeValues": {
                            ":status": serializer.serialize(Asset_Status_Enum.ASSIGNED),
                            ":sipk": serializer.serialize(
                                f"STATUS#{Asset_Status_Enum.ASSIGNED.value}"
                            ),
                            ":expected_status": serializer.serialize(
                                Asset_Status_Enum.IN_STOCK
                            ),
                        },
                    }
                },
                {"Put": {"TableName": ASSETS_TABLE, "Item": audit_item}},
            ]
        )

        response = AcceptHandoverResponse(
            asset_id=asset_id,
            status=Asset_Status_Enum.ASSIGNED,
            signed_form_url=signed_form_url,
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
