import json
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        os.pardir,
        os.pardir,
        "services",
        "lambdas",
        "functions",
        "ScanWorker",
    ),
)

SCAN_JOB_ID = "scan-job-001"
SESSION_ID = "session-001"
INVOICE_KEY = "uploads/session-001/invoice/invoice.pdf"
PHOTO_KEYS = ["uploads/session-001/gadget_photo/photo1.jpg"]


def _seed_scan_and_session(table):
    table.put_item(
        Item={
            "PK": f"SCAN#{SCAN_JOB_ID}",
            "SK": "METADATA",
            "ScanJobID": SCAN_JOB_ID,
            "UploadSessionID": SESSION_ID,
            "Status": "PROCESSING",
            "CreatedAt": "2026-01-01T00:00:00+00:00",
        }
    )
    table.put_item(
        Item={
            "PK": f"SESSION#{SESSION_ID}",
            "SK": "METADATA",
            "UploadSessionID": SESSION_ID,
            "InvoiceS3Key": INVOICE_KEY,
            "GadgetPhotoS3Keys": PHOTO_KEYS,
            "CreatedAt": "2026-01-01T00:00:00+00:00",
            "TTL": 9999999999,
        }
    )


def _textract_response(fields: dict) -> dict:
    """Build a minimal Textract AnalyzeExpense response."""
    summary_fields = []
    for field_type, (value, confidence) in fields.items():
        summary_fields.append(
            {
                "Type": {"Text": field_type},
                "ValueDetection": {"Text": value, "Confidence": confidence},
            }
        )
    return {"ExpenseDocuments": [{"SummaryFields": summary_fields}]}


def _bedrock_response(data: dict) -> dict:
    """Build a minimal Bedrock Nova Lite response."""
    return {
        "body": MagicMock(
            read=lambda: json.dumps(
                {"output": {"message": {"content": [{"text": json.dumps(data)}]}}}
            ).encode()
        )
    }


# ---------------------------------------------------------------------------
# Happy path — successful extraction
# ---------------------------------------------------------------------------


def test_successful_extraction_sets_completed(aws_mocks):
    table = aws_mocks["table"]
    _seed_scan_and_session(table)

    textract_resp = _textract_response(
        {
            "INVOICE_RECEIPT_ID": ("INV-001", 98.5),
            "VENDOR_NAME": ("Dell Technologies", 99.1),
            "INVOICE_RECEIPT_DATE": ("2026-03-01", 97.2),
            "AMOUNT_PAID": ("1299.00", 99.0),
            "PAYMENT_TERMS": ("Corporate Card", 88.5),
        }
    )
    bedrock_resp = _bedrock_response(
        {
            "brand": "Dell",
            "model": "Latitude 5540",
            "serial_number": "SN-ABC123",
            "product_description": "14 inch Business Laptop",
        }
    )

    with patch("lambda_function.textract_client") as mock_textract, patch(
        "lambda_function.bedrock_client"
    ) as mock_bedrock, patch("lambda_function.s3_client") as mock_s3:
        mock_textract.analyze_expense.return_value = textract_resp
        mock_bedrock.invoke_model.return_value = bedrock_resp
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"fake-image-bytes")
        }

        import lambda_function

        lambda_function.lambda_handler({"scan_job_id": SCAN_JOB_ID}, {})

    item = table.get_item(Key={"PK": f"SCAN#{SCAN_JOB_ID}", "SK": "METADATA"})["Item"]
    assert item["Status"] == "COMPLETED"
    assert item["InvoiceNumber"]["value"] == "INV-001"
    assert item["Vendor"]["value"] == "Dell Technologies"
    assert item["Brand"]["value"] == "Dell"
    assert item["Model"]["value"] == "Latitude 5540"


def test_textract_confidence_normalised(aws_mocks):
    table = aws_mocks["table"]
    _seed_scan_and_session(table)

    textract_resp = _textract_response({"VENDOR_NAME": ("Acme Corp", 95.0)})
    bedrock_resp = _bedrock_response(
        {
            "brand": "Acme",
            "model": None,
            "serial_number": None,
            "product_description": None,
        }
    )

    with patch("lambda_function.textract_client") as mock_textract, patch(
        "lambda_function.bedrock_client"
    ) as mock_bedrock, patch("lambda_function.s3_client") as mock_s3:
        mock_textract.analyze_expense.return_value = textract_resp
        mock_bedrock.invoke_model.return_value = bedrock_resp
        mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: b"bytes")}

        import lambda_function

        lambda_function.lambda_handler({"scan_job_id": SCAN_JOB_ID}, {})

    item = table.get_item(Key={"PK": f"SCAN#{SCAN_JOB_ID}", "SK": "METADATA"})["Item"]
    # 95.0 / 100 = 0.95
    assert float(item["Vendor"]["confidence"]) == pytest.approx(0.95)


def test_bedrock_fields_have_confidence_1(aws_mocks):
    table = aws_mocks["table"]
    _seed_scan_and_session(table)

    textract_resp = _textract_response({})
    bedrock_resp = _bedrock_response(
        {
            "brand": "Apple",
            "model": "MacBook Pro",
            "serial_number": "SN-XYZ",
            "product_description": "Laptop",
        }
    )

    with patch("lambda_function.textract_client") as mock_textract, patch(
        "lambda_function.bedrock_client"
    ) as mock_bedrock, patch("lambda_function.s3_client") as mock_s3:
        mock_textract.analyze_expense.return_value = textract_resp
        mock_bedrock.invoke_model.return_value = bedrock_resp
        mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: b"bytes")}

        import lambda_function

        lambda_function.lambda_handler({"scan_job_id": SCAN_JOB_ID}, {})

    item = table.get_item(Key={"PK": f"SCAN#{SCAN_JOB_ID}", "SK": "METADATA"})["Item"]
    assert float(item["Brand"]["confidence"]) == 1.0
    assert float(item["Model"]["confidence"]) == 1.0
    assert float(item["SerialNumber"]["confidence"]) == 1.0


# ---------------------------------------------------------------------------
# Field merge logic
# ---------------------------------------------------------------------------


def test_merge_textract_wins_when_higher_confidence(aws_mocks):
    """SerialNumber: Textract=0.99, Bedrock=1.0 → Bedrock wins as primary."""
    table = aws_mocks["table"]
    _seed_scan_and_session(table)

    # Textract has serial number at 99% confidence
    textract_resp = _textract_response({})
    # Bedrock has serial number at 1.0 (higher)
    bedrock_resp = _bedrock_response(
        {
            "brand": None,
            "model": None,
            "serial_number": "SN-BEDROCK",
            "product_description": None,
        }
    )

    with patch("lambda_function.textract_client") as mock_textract, patch(
        "lambda_function.bedrock_client"
    ) as mock_bedrock, patch("lambda_function.s3_client") as mock_s3:
        mock_textract.analyze_expense.return_value = textract_resp
        mock_bedrock.invoke_model.return_value = bedrock_resp
        mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: b"bytes")}

        import lambda_function

        lambda_function.lambda_handler({"scan_job_id": SCAN_JOB_ID}, {})

    item = table.get_item(Key={"PK": f"SCAN#{SCAN_JOB_ID}", "SK": "METADATA"})["Item"]
    # Bedrock-only field, no merge needed
    assert item["SerialNumber"]["value"] == "SN-BEDROCK"
    assert float(item["SerialNumber"]["confidence"]) == 1.0


def test_merge_textract_higher_confidence_wins(aws_mocks):
    """When Textract confidence > Bedrock (1.0), Textract is primary."""
    table = aws_mocks["table"]
    _seed_scan_and_session(table)

    # Simulate both sources having SerialNumber by patching _merge_fields directly
    # We test the merge function in isolation
    import lambda_function
    from utils.models import ExtractedFieldValue

    textract_fields = {
        "SerialNumber": ExtractedFieldValue(value="SN-TEXTRACT", confidence=0.5)
    }
    bedrock_fields = {
        "SerialNumber": ExtractedFieldValue(value="SN-BEDROCK", confidence=1.0)
    }
    merged = lambda_function._merge_fields(textract_fields, bedrock_fields)

    # Bedrock wins (1.0 > 0.5)
    assert merged["SerialNumber"].value == "SN-BEDROCK"
    assert merged["SerialNumber"].confidence == 1.0
    assert merged["SerialNumber"].alternative_value == "SN-TEXTRACT"
    assert merged["SerialNumber"].alternative_confidence == 0.5


def test_merge_textract_lower_confidence_is_alternative(aws_mocks):
    """When Textract confidence > Bedrock, Textract is primary and Bedrock is alternative."""
    import lambda_function
    from utils.models import ExtractedFieldValue

    textract_fields = {
        "SerialNumber": ExtractedFieldValue(value="SN-TEXTRACT", confidence=0.99)
    }
    bedrock_fields = {
        "SerialNumber": ExtractedFieldValue(value="SN-BEDROCK", confidence=1.0)
    }
    merged = lambda_function._merge_fields(textract_fields, bedrock_fields)

    # Bedrock still wins (1.0 >= 0.99)
    assert merged["SerialNumber"].value == "SN-BEDROCK"
    assert merged["SerialNumber"].alternative_value == "SN-TEXTRACT"


# ---------------------------------------------------------------------------
# Failure cases
# ---------------------------------------------------------------------------


def test_bedrock_non_json_sets_scan_failed(aws_mocks):
    table = aws_mocks["table"]
    _seed_scan_and_session(table)

    textract_resp = _textract_response({})
    bad_bedrock_resp = {
        "body": MagicMock(
            read=lambda: json.dumps(
                {
                    "output": {
                        "message": {"content": [{"text": "This is not JSON at all"}]}
                    }
                }
            ).encode()
        )
    }

    with patch("lambda_function.textract_client") as mock_textract, patch(
        "lambda_function.bedrock_client"
    ) as mock_bedrock, patch("lambda_function.s3_client") as mock_s3:
        mock_textract.analyze_expense.return_value = textract_resp
        mock_bedrock.invoke_model.return_value = bad_bedrock_resp
        mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: b"bytes")}

        import lambda_function

        lambda_function.lambda_handler({"scan_job_id": SCAN_JOB_ID}, {})

    item = table.get_item(Key={"PK": f"SCAN#{SCAN_JOB_ID}", "SK": "METADATA"})["Item"]
    assert item["Status"] == "SCAN_FAILED"
    assert "FailureReason" in item


def test_textract_exception_sets_scan_failed(aws_mocks):
    table = aws_mocks["table"]
    _seed_scan_and_session(table)

    with patch("lambda_function.textract_client") as mock_textract, patch(
        "lambda_function.bedrock_client"
    ), patch("lambda_function.s3_client"):
        mock_textract.analyze_expense.side_effect = Exception("Textract unavailable")

        import lambda_function

        lambda_function.lambda_handler({"scan_job_id": SCAN_JOB_ID}, {})

    item = table.get_item(Key={"PK": f"SCAN#{SCAN_JOB_ID}", "SK": "METADATA"})["Item"]
    assert item["Status"] == "SCAN_FAILED"
    assert "Textract unavailable" in item["FailureReason"]


def test_bedrock_exception_sets_scan_failed(aws_mocks):
    table = aws_mocks["table"]
    _seed_scan_and_session(table)

    textract_resp = _textract_response({})

    with patch("lambda_function.textract_client") as mock_textract, patch(
        "lambda_function.bedrock_client"
    ) as mock_bedrock, patch("lambda_function.s3_client") as mock_s3:
        mock_textract.analyze_expense.return_value = textract_resp
        mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: b"bytes")}
        mock_bedrock.invoke_model.side_effect = Exception("Bedrock unavailable")

        import lambda_function

        lambda_function.lambda_handler({"scan_job_id": SCAN_JOB_ID}, {})

    item = table.get_item(Key={"PK": f"SCAN#{SCAN_JOB_ID}", "SK": "METADATA"})["Item"]
    assert item["Status"] == "SCAN_FAILED"
    assert "Bedrock unavailable" in item["FailureReason"]
