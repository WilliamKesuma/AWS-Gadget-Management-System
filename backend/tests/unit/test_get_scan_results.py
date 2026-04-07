import json
import sys
import os
import pytest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        os.pardir,
        os.pardir,
        "services",
        "lambdas",
        "functions",
        "GetScanResults",
    ),
)

SCAN_JOB_ID = "scan-job-get-001"


def _make_event(scan_job_id: str = SCAN_JOB_ID, group: str = "it-admin") -> dict:
    return {
        "pathParameters": {"scan_job_id": scan_job_id},
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "admin-user-id-1234",
                    "cognito:groups": group,
                }
            }
        },
    }


def _seed_scan_job(table, status: str, extra: dict = None):
    item = {
        "PK": f"SCAN#{SCAN_JOB_ID}",
        "SK": "METADATA",
        "ScanJobID": SCAN_JOB_ID,
        "UploadSessionID": "session-001",
        "Status": status,
        "CreatedAt": "2026-01-01T00:00:00+00:00",
    }
    if extra:
        item.update(extra)
    table.put_item(Item=item)


# ---------------------------------------------------------------------------
# PROCESSING
# ---------------------------------------------------------------------------


def test_processing_returns_status_only(aws_mocks):
    _seed_scan_job(aws_mocks["table"], "PROCESSING")

    import lambda_function

    result = lambda_function.lambda_handler(_make_event(), {})

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["status"] == "PROCESSING"
    assert "extracted_fields" not in body


# ---------------------------------------------------------------------------
# COMPLETED
# ---------------------------------------------------------------------------


def test_completed_returns_extracted_fields(aws_mocks):
    _seed_scan_job(
        aws_mocks["table"],
        "COMPLETED",
        extra={
            "InvoiceNumber": {"value": "INV-001", "confidence": 0.985},
            "Vendor": {"value": "Dell Technologies", "confidence": 0.991},
            "Brand": {"value": "Dell", "confidence": 1.0},
            "Model": {"value": "Latitude 5540", "confidence": 1.0},
            "SerialNumber": {"value": "SN-ABC123", "confidence": 1.0},
        },
    )

    import lambda_function

    result = lambda_function.lambda_handler(_make_event(), {})

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["status"] == "COMPLETED"
    fields = body["extracted_fields"]
    assert fields["invoice_number"]["value"] == "INV-001"
    assert fields["invoice_number"]["confidence"] == pytest.approx(0.985)
    assert fields["vendor"]["value"] == "Dell Technologies"
    assert fields["brand"]["value"] == "Dell"
    assert fields["model"]["confidence"] == 1.0


def test_completed_includes_alternative_values(aws_mocks):
    _seed_scan_job(
        aws_mocks["table"],
        "COMPLETED",
        extra={
            "SerialNumber": {
                "value": "SN-PRIMARY",
                "confidence": 1.0,
                "alternative_value": "SN-ALT",
                "alternative_confidence": 0.85,
            },
        },
    )

    import lambda_function

    result = lambda_function.lambda_handler(_make_event(), {})

    body = json.loads(result["body"])
    sn = body["extracted_fields"]["serial_number"]
    assert sn["value"] == "SN-PRIMARY"
    assert sn["alternative_value"] == "SN-ALT"
    assert sn["alternative_confidence"] == pytest.approx(0.85)


# ---------------------------------------------------------------------------
# SCAN_FAILED
# ---------------------------------------------------------------------------


def test_scan_failed_returns_failure_reason(aws_mocks):
    _seed_scan_job(
        aws_mocks["table"], "SCAN_FAILED", extra={"FailureReason": "Textract timed out"}
    )

    import lambda_function

    result = lambda_function.lambda_handler(_make_event(), {})

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["status"] == "SCAN_FAILED"
    assert body["failure_reason"] == "Textract timed out"


# ---------------------------------------------------------------------------
# Not found
# ---------------------------------------------------------------------------


def test_nonexistent_scan_job_returns_404(aws_mocks):
    import lambda_function

    result = lambda_function.lambda_handler(_make_event("nonexistent-id"), {})

    assert result["statusCode"] == 404
    assert "Scan job not found" in json.loads(result["body"])["message"]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_non_it_admin_returns_403(aws_mocks):
    _seed_scan_job(aws_mocks["table"], "PROCESSING")

    import lambda_function

    result = lambda_function.lambda_handler(_make_event(group="employee"), {})

    assert result["statusCode"] == 403
