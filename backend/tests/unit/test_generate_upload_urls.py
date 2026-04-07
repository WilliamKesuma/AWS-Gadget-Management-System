import json
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Add Lambda function directory to path
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        os.pardir,
        os.pardir,
        "services",
        "lambdas",
        "functions",
        "GenerateUploadUrls",
    ),
)

SCAN_WORKER_ARN = (
    "arn:aws:lambda:ap-southeast-1:123456789012:function:gms-dev-scan-worker"
)


@pytest.fixture(autouse=True)
def set_scan_worker_env(monkeypatch):
    monkeypatch.setenv("SCAN_WORKER_ARN", SCAN_WORKER_ARN)


def _make_event(body: dict, group: str = "it-admin") -> dict:
    return {
        "body": json.dumps(body),
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "admin-user-id-1234",
                    "cognito:groups": group,
                }
            }
        },
    }


def _valid_files():
    return [
        {"name": "invoice.pdf", "content_type": "application/pdf", "type": "invoice"},
        {"name": "photo1.jpg", "content_type": "image/jpeg", "type": "gadget_photo"},
    ]


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_returns_upload_session_id_scan_job_id_and_urls(aws_mocks, monkeypatch):
    monkeypatch.setenv("SCAN_WORKER_ARN", SCAN_WORKER_ARN)

    with patch("lambda_function.s3_client") as mock_s3, patch(
        "lambda_function.lambda_client"
    ) as mock_lambda:
        mock_s3.generate_presigned_url.return_value = "https://s3.example.com/presigned"
        mock_lambda.invoke.return_value = {"StatusCode": 202}

        import lambda_function

        event = _make_event({"files": _valid_files()})
        result = lambda_function.lambda_handler(event, {})

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert "upload_session_id" in body
    assert "scan_job_id" in body
    assert len(body["urls"]) == 2


def test_s3_key_format(aws_mocks, monkeypatch):
    monkeypatch.setenv("SCAN_WORKER_ARN", SCAN_WORKER_ARN)

    with patch("lambda_function.s3_client") as mock_s3, patch(
        "lambda_function.lambda_client"
    ) as mock_lambda:
        mock_s3.generate_presigned_url.return_value = "https://s3.example.com/presigned"
        mock_lambda.invoke.return_value = {"StatusCode": 202}

        import lambda_function

        event = _make_event({"files": _valid_files()})
        result = lambda_function.lambda_handler(event, {})

    body = json.loads(result["body"])
    session_id = body["upload_session_id"]
    keys = [u["file_key"] for u in body["urls"]]

    assert any(k.startswith(f"uploads/{session_id}/invoice/") for k in keys)
    assert any(k.startswith(f"uploads/{session_id}/gadget_photo/") for k in keys)


def test_session_and_scan_job_written_to_dynamodb(aws_mocks, monkeypatch):
    monkeypatch.setenv("SCAN_WORKER_ARN", SCAN_WORKER_ARN)
    table = aws_mocks["table"]

    with patch("lambda_function.s3_client") as mock_s3, patch(
        "lambda_function.lambda_client"
    ) as mock_lambda:
        mock_s3.generate_presigned_url.return_value = "https://s3.example.com/presigned"
        mock_lambda.invoke.return_value = {"StatusCode": 202}

        import lambda_function

        event = _make_event({"files": _valid_files()})
        result = lambda_function.lambda_handler(event, {})

    body = json.loads(result["body"])
    session_id = body["upload_session_id"]
    scan_job_id = body["scan_job_id"]

    session_item = table.get_item(
        Key={"PK": f"SESSION#{session_id}", "SK": "METADATA"}
    )["Item"]
    assert session_item["UploadSessionID"] == session_id

    scan_item = table.get_item(Key={"PK": f"SCAN#{scan_job_id}", "SK": "METADATA"})[
        "Item"
    ]
    assert scan_item["Status"] == "PROCESSING"
    assert scan_item["UploadSessionID"] == session_id


def test_scan_worker_invoked_async(aws_mocks, monkeypatch):
    monkeypatch.setenv("SCAN_WORKER_ARN", SCAN_WORKER_ARN)

    with patch("lambda_function.s3_client") as mock_s3, patch(
        "lambda_function.lambda_client"
    ) as mock_lambda:
        mock_s3.generate_presigned_url.return_value = "https://s3.example.com/presigned"
        mock_lambda.invoke.return_value = {"StatusCode": 202}

        import lambda_function

        event = _make_event({"files": _valid_files()})
        result = lambda_function.lambda_handler(event, {})

    body = json.loads(result["body"])
    scan_job_id = body["scan_job_id"]

    call_kwargs = mock_lambda.invoke.call_args
    assert call_kwargs.kwargs["InvocationType"] == "Event"
    assert call_kwargs.kwargs["FunctionName"] == SCAN_WORKER_ARN
    payload = json.loads(call_kwargs.kwargs["Payload"])
    assert payload["scan_job_id"] == scan_job_id


# ---------------------------------------------------------------------------
# File count validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "files,expected_msg",
    [
        # 0 invoices
        (
            [{"name": "p.jpg", "content_type": "image/jpeg", "type": "gadget_photo"}],
            "Exactly one invoice file is required",
        ),
        # 2 invoices
        (
            [
                {
                    "name": "inv1.pdf",
                    "content_type": "application/pdf",
                    "type": "invoice",
                },
                {
                    "name": "inv2.pdf",
                    "content_type": "application/pdf",
                    "type": "invoice",
                },
                {"name": "p.jpg", "content_type": "image/jpeg", "type": "gadget_photo"},
            ],
            "Exactly one invoice file is required",
        ),
        # 0 photos
        (
            [{"name": "inv.pdf", "content_type": "application/pdf", "type": "invoice"}],
            "At least one gadget photo is required",
        ),
        # 6 photos
        (
            [{"name": "inv.pdf", "content_type": "application/pdf", "type": "invoice"}]
            + [
                {
                    "name": f"p{i}.jpg",
                    "content_type": "image/jpeg",
                    "type": "gadget_photo",
                }
                for i in range(6)
            ],
            "Maximum of five gadget photos allowed",
        ),
    ],
)
def test_file_count_validation(aws_mocks, monkeypatch, files, expected_msg):
    monkeypatch.setenv("SCAN_WORKER_ARN", SCAN_WORKER_ARN)

    with patch("lambda_function.s3_client"), patch("lambda_function.lambda_client"):
        import lambda_function

        result = lambda_function.lambda_handler(_make_event({"files": files}), {})

    assert result["statusCode"] == 400
    assert expected_msg in json.loads(result["body"])["message"]


# ---------------------------------------------------------------------------
# Content-type validation
# ---------------------------------------------------------------------------


def test_gadget_photo_non_image_rejected(aws_mocks, monkeypatch):
    monkeypatch.setenv("SCAN_WORKER_ARN", SCAN_WORKER_ARN)
    files = [
        {"name": "inv.pdf", "content_type": "application/pdf", "type": "invoice"},
        {"name": "doc.pdf", "content_type": "application/pdf", "type": "gadget_photo"},
    ]
    with patch("lambda_function.s3_client"), patch("lambda_function.lambda_client"):
        import lambda_function

        result = lambda_function.lambda_handler(_make_event({"files": files}), {})

    assert result["statusCode"] == 400
    assert "Gadget photos must be image files" in json.loads(result["body"])["message"]


def test_invoice_non_pdf_non_image_rejected(aws_mocks, monkeypatch):
    monkeypatch.setenv("SCAN_WORKER_ARN", SCAN_WORKER_ARN)
    files = [
        {
            "name": "inv.xlsx",
            "content_type": "application/vnd.ms-excel",
            "type": "invoice",
        },
        {"name": "p.jpg", "content_type": "image/jpeg", "type": "gadget_photo"},
    ]
    with patch("lambda_function.s3_client"), patch("lambda_function.lambda_client"):
        import lambda_function

        result = lambda_function.lambda_handler(_make_event({"files": files}), {})

    assert result["statusCode"] == 400
    assert (
        "Invoice must be a PDF or image file" in json.loads(result["body"])["message"]
    )


def test_invoice_image_accepted(aws_mocks, monkeypatch):
    monkeypatch.setenv("SCAN_WORKER_ARN", SCAN_WORKER_ARN)
    files = [
        {"name": "inv.jpg", "content_type": "image/jpeg", "type": "invoice"},
        {"name": "p.jpg", "content_type": "image/jpeg", "type": "gadget_photo"},
    ]
    with patch("lambda_function.s3_client") as mock_s3, patch(
        "lambda_function.lambda_client"
    ) as mock_lambda:
        mock_s3.generate_presigned_url.return_value = "https://s3.example.com/presigned"
        mock_lambda.invoke.return_value = {"StatusCode": 202}

        import lambda_function

        result = lambda_function.lambda_handler(_make_event({"files": files}), {})

    assert result["statusCode"] == 200


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_non_it_admin_returns_403(aws_mocks, monkeypatch):
    monkeypatch.setenv("SCAN_WORKER_ARN", SCAN_WORKER_ARN)
    with patch("lambda_function.s3_client"), patch("lambda_function.lambda_client"):
        import lambda_function

        result = lambda_function.lambda_handler(
            _make_event({"files": _valid_files()}, group="employee"), {}
        )

    assert result["statusCode"] == 403
