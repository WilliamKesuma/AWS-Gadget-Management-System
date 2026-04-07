import os

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer

from custom_exceptions import NotFoundException
from utils import error, success, get_item
from utils.auth import require_group
from utils.enums import Scan_Status_Enum, User_Role_Enum
from utils.models import ExtractedFieldValue, ScanJobModel

from model import GetScanResultsResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)

# Map ScanJobModel field names to snake_case response keys
_FIELD_MAP = {
    "InvoiceNumber": "invoice_number",
    "Vendor": "vendor",
    "PurchaseDate": "purchase_date",
    "SerialNumber": "serial_number",
    "Brand": "brand",
    "Model": "model",
    "ProductDescription": "product_description",
    "Cost": "cost",
    "PaymentMethod": "payment_method",
    "Processor": "processor",
    "Storage": "storage",
    "OSVersion": "os_version",
    "Memory": "memory",
}


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        require_group(event, User_Role_Enum.IT_ADMIN)

        scan_job_id = event["pathParameters"]["scan_job_id"]

        item = get_item(table, {"PK": f"SCAN#{scan_job_id}", "SK": "METADATA"})
        if not item:
            raise NotFoundException("Scan job not found")

        scan_job = ScanJobModel(**item)

        if scan_job.Status == Scan_Status_Enum.PROCESSING:
            return success({"status": Scan_Status_Enum.PROCESSING.value})

        if scan_job.Status == Scan_Status_Enum.SCAN_FAILED:
            return {
                "statusCode": 422,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key",
                    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
                },
                "body": json.dumps(
                    GetScanResultsResponse(
                        status=Scan_Status_Enum.SCAN_FAILED.value,
                        failure_reason=scan_job.FailureReason,
                    ).model_dump(exclude_none=True)
                ),
            }

        # COMPLETED — build extracted_fields dict
        extracted_fields = {}
        for model_field, response_key in _FIELD_MAP.items():
            field_val: ExtractedFieldValue | None = getattr(scan_job, model_field, None)
            if field_val is not None:
                entry = {"value": field_val.value, "confidence": field_val.confidence}
                if field_val.alternative_value is not None:
                    entry["alternative_value"] = field_val.alternative_value
                    entry["alternative_confidence"] = field_val.alternative_confidence
                extracted_fields[response_key] = entry

        return success(
            GetScanResultsResponse(
                status=Scan_Status_Enum.COMPLETED.value,
                extracted_fields=extracted_fields,
            ).model_dump(exclude_none=True)
        )

    except NotFoundException as e:
        return error(str(e), 404)
    except PermissionError as e:
        return error(str(e), 403)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
