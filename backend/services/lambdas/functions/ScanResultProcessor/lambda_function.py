import json
import os
from decimal import Decimal

import boto3
from aws_lambda_powertools import Logger, Tracer

from utils.enums import Scan_Status_Enum
from utils.models import ExtractedFieldValue

from model import TextractSNSMessage

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
textract_client = boto3.client(
    "textract", region_name=os.environ.get("AWS_REGION", "ap-southeast-1")
)


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


def _get_all_blocks(job_id: str) -> list[dict]:
    """Paginate through GetDocumentAnalysis to collect all blocks."""
    blocks = []
    response = textract_client.get_document_analysis(JobId=job_id)
    blocks.extend(response.get("Blocks", []))

    while next_token := response.get("NextToken"):
        response = textract_client.get_document_analysis(
            JobId=job_id, NextToken=next_token
        )
        blocks.extend(response.get("Blocks", []))

    return blocks


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
        # Parse SNS message
        sns_record = event["Records"][0]["Sns"]
        message = json.loads(sns_record["Message"])
        textract_msg = TextractSNSMessage(**message)

        job_id = textract_msg.JobId
        scan_job_id = textract_msg.JobTag

        if not scan_job_id:
            logger.error("No JobTag (scan_job_id) in Textract SNS message")
            return

        logger.info(
            "Processing Textract result",
            scan_job_id=scan_job_id,
            textract_job_id=job_id,
            textract_status=textract_msg.Status,
        )

        if textract_msg.Status != "SUCCEEDED":
            _update_scan_job(
                scan_job_id,
                {
                    "Status": Scan_Status_Enum.SCAN_FAILED.value,
                    "FailureReason": f"Textract job {textract_msg.Status}",
                },
            )
            return

        # Fetch all result blocks and parse query answers
        blocks = _get_all_blocks(job_id)
        fields = _parse_query_results(blocks)

        updates = {"Status": Scan_Status_Enum.COMPLETED.value}
        for name, efv in fields.items():
            updates[name] = efv.model_dump(exclude_none=True)

        _update_scan_job(scan_job_id, _to_decimal(updates))
        logger.info("Scan job completed (async)", scan_job_id=scan_job_id)

    except Exception as e:
        logger.exception("ScanResultProcessor failed", scan_job_id=scan_job_id)
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
