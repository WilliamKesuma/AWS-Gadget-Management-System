import os
import time
from decimal import Decimal

import boto3
import cv2
import numpy as np
from aws_lambda_powertools import Logger, Tracer
from botocore.exceptions import ClientError

from utils import get_item
from utils.enums import Scan_Status_Enum
from utils.models import ExtractedFieldValue, ScanJobModel, UploadSessionModel

from model import ScanWorkerEvent

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]
ASSETS_BUCKET = os.environ["ASSETS_BUCKET"]
SNS_TOPIC_ARN = os.environ.get("TEXTRACT_SNS_TOPIC_ARN", "")
SNS_ROLE_ARN = os.environ.get("TEXTRACT_SNS_ROLE_ARN", "")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
s3_client = boto3.client("s3")
textract_client = boto3.client(
    "textract", region_name=os.environ.get("AWS_REGION", "ap-southeast-1")
)

INVOICE_QUERIES = [
    {
        "Text": "What is the invoice or receipt number?",
        "Alias": "InvoiceNumber",
        "Pages": ["*"],
    },
    {"Text": "Who is the vendor or seller?", "Alias": "Vendor", "Pages": ["*"]},
    {
        "Text": "What is the purchase or invoice date?",
        "Alias": "PurchaseDate",
        "Pages": ["*"],
    },
    {
        "Text": "What is the brand or manufacturer of the item?",
        "Alias": "Brand",
        "Pages": ["*"],
    },
    {
        "Text": "What is the model name or model number of the item?",
        "Alias": "Model",
        "Pages": ["*"],
    },
    {
        "Text": "What is the serial number of the item?",
        "Alias": "SerialNumber",
        "Pages": ["*"],
    },
    {
        "Text": "What is the product description or item description?",
        "Alias": "ProductDescription",
        "Pages": ["*"],
    },
    {
        "Text": "What is the total cost or total amount due?",
        "Alias": "Cost",
        "Pages": ["*"],
    },
    {
        "Text": "What is the payment method, such as bank transfer, credit card, or cash?",
        "Alias": "PaymentMethod",
        "Pages": ["*"],
    },
    {
        "Text": "What is the processor or CPU of the item?",
        "Alias": "Processor",
        "Pages": ["*"],
    },
    {
        "Text": "What is the storage capacity or hard drive size?",
        "Alias": "Storage",
        "Pages": ["*"],
    },
    {
        "Text": "What is the operating system version?",
        "Alias": "OSVersion",
        "Pages": ["*"],
    },
    {
        "Text": "What is the memory or RAM size?",
        "Alias": "Memory",
        "Pages": ["*"],
    },
]

S3_WAIT_RETRIES = 10
S3_WAIT_DELAY = 5.0


def _wait_for_s3_object(key: str) -> None:
    for attempt in range(S3_WAIT_RETRIES):
        try:
            s3_client.head_object(Bucket=ASSETS_BUCKET, Key=key)
            return
        except ClientError as e:
            code = e.response["Error"]["Code"]
            # Without s3:ListBucket, S3 returns 403 instead of 404 for
            # non-existent objects. Treat both as "not yet uploaded".
            if code in ("404", "NoSuchKey", "403", "Forbidden"):
                if attempt < S3_WAIT_RETRIES - 1:
                    logger.info(f"Waiting for S3 object {key}, attempt {attempt + 1}")
                    time.sleep(S3_WAIT_DELAY)
                else:
                    raise RuntimeError(
                        f"S3 object not found after {S3_WAIT_RETRIES} attempts: {key}"
                    )
            else:
                raise


BLUR_THRESHOLD = 100.0  # Laplacian variance below this is considered blurry

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}


def _is_pdf(key: str) -> bool:
    return os.path.splitext(key)[1].lower() == ".pdf"


def _is_image(key: str) -> bool:
    return os.path.splitext(key)[1].lower() in IMAGE_EXTENSIONS


def _detect_blur(s3_key: str) -> float:
    """Download image from S3 and return Laplacian variance. Lower = more blurry."""
    response = s3_client.get_object(Bucket=ASSETS_BUCKET, Key=s3_key)
    image_bytes = response["Body"].read()
    np_array = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(np_array, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"Could not decode image from S3 key: {s3_key}")
    return cv2.Laplacian(image, cv2.CV_64F).var()


def _parse_query_results(blocks: list[dict]) -> dict[str, ExtractedFieldValue]:
    block_map = {b["Id"]: b for b in blocks}
    fields: dict[str, ExtractedFieldValue] = {}

    for block in blocks:
        if block.get("BlockType") != "QUERY":
            continue
        alias = block.get("Query", {}).get("Alias", "")
        if not alias:
            continue
        for rel in block.get("Relationships", []):
            if rel.get("Type") != "ANSWER":
                continue
            for rid in rel.get("Ids", []):
                rb = block_map.get(rid, {})
                value = rb.get("Text", "").strip()
                confidence = round(rb.get("Confidence", 0.0) / 100.0, 4)
                if not value or value.upper() in ("", "N/A", "NONE", "NOT FOUND"):
                    continue
                if alias not in fields or confidence > fields[alias].confidence:
                    fields[alias] = ExtractedFieldValue(
                        value=value, confidence=confidence
                    )
    return fields


def _extract_fields_sync(invoice_key: str) -> dict[str, ExtractedFieldValue]:
    """Sync Textract AnalyzeDocument with QUERIES — for images only."""
    queries = [{"Text": q["Text"], "Alias": q["Alias"]} for q in INVOICE_QUERIES]
    response = textract_client.analyze_document(
        Document={"S3Object": {"Bucket": ASSETS_BUCKET, "Name": invoice_key}},
        FeatureTypes=["QUERIES"],
        QueriesConfig={"Queries": queries},
    )
    return _parse_query_results(response.get("Blocks", []))


def _start_async_job(invoice_key: str, scan_job_id: str) -> str:
    """Start async Textract job with SNS notification for PDFs. Returns Textract JobId."""
    start_params = {
        "DocumentLocation": {
            "S3Object": {"Bucket": ASSETS_BUCKET, "Name": invoice_key}
        },
        "FeatureTypes": ["QUERIES"],
        "QueriesConfig": {"Queries": INVOICE_QUERIES},
        "NotificationChannel": {
            "SNSTopicArn": SNS_TOPIC_ARN,
            "RoleArn": SNS_ROLE_ARN,
        },
        "JobTag": scan_job_id,
    }
    result = textract_client.start_document_analysis(**start_params)
    return result["JobId"]


def _to_decimal(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_decimal(i) for i in obj]
    return obj


def _update_scan_job(scan_job_id: str, updates: dict) -> None:
    expr_parts, names, values = [], {}, {}
    for k, v in updates.items():
        expr_parts.append(f"#{k} = :{k}")
        names[f"#{k}"] = k
        values[f":{k}"] = v

    table.update_item(
        Key={"PK": f"SCAN#{scan_job_id}", "SK": "METADATA"},
        UpdateExpression="SET " + ", ".join(expr_parts),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    scan_job_id = None
    try:
        scan_job_id = ScanWorkerEvent(**event).scan_job_id

        scan_job = ScanJobModel(
            **get_item(table, {"PK": f"SCAN#{scan_job_id}", "SK": "METADATA"})
        )
        session = UploadSessionModel(
            **get_item(
                table, {"PK": f"SESSION#{scan_job.UploadSessionID}", "SK": "METADATA"}
            )
        )

        _wait_for_s3_object(session.InvoiceS3Key)

        if _is_pdf(session.InvoiceS3Key):
            # Async path: start Textract job with SNS notification, then exit.
            # ScanResultProcessor Lambda will handle the completion callback.
            textract_job_id = _start_async_job(session.InvoiceS3Key, scan_job_id)
            _update_scan_job(scan_job_id, {"TextractJobId": textract_job_id})
            logger.info(
                "Started async Textract job, awaiting SNS callback",
                scan_job_id=scan_job_id,
                textract_job_id=textract_job_id,
            )
        else:
            # Sync path: images complete instantly
            if _is_image(session.InvoiceS3Key):
                blur_score = _detect_blur(session.InvoiceS3Key)
                logger.info(
                    "Blur detection score", score=blur_score, scan_job_id=scan_job_id
                )
                if blur_score < BLUR_THRESHOLD:
                    raise ValueError(
                        f"Image is too blurry to process (score: {blur_score:.2f}). "
                        "Please upload a clearer image."
                    )

            fields = _extract_fields_sync(session.InvoiceS3Key)
            updates = {"Status": Scan_Status_Enum.COMPLETED.value}
            for name, efv in fields.items():
                updates[name] = efv.model_dump(exclude_none=True)
            _update_scan_job(scan_job_id, _to_decimal(updates))
            logger.info("Scan job completed (sync)", scan_job_id=scan_job_id)

    except Exception as e:
        logger.exception("ScanWorker failed", scan_job_id=scan_job_id)
        if scan_job_id:
            try:
                _update_scan_job(
                    scan_job_id,
                    {
                        "Status": Scan_Status_Enum.SCAN_FAILED.value,
                        "FailureReason": str(e),
                    },
                )
            except Exception:
                logger.exception("Failed to update scan job status to SCAN_FAILED")
