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
        "CreateAsset",
    ),
)

SCAN_JOB_ID = "scan-job-create-001"
SESSION_ID = "session-create-001"
ACTOR_ID = "admin-user-id-1234"


class _FakeLambdaContext:
    """Minimal Lambda context for aws_lambda_powertools decorators."""

    function_name = "test-create-asset"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:ap-southeast-1:123456789012:function:test"
    aws_request_id = "test-request-id"


_CTX = _FakeLambdaContext()


def _make_event(body: dict, group: str = "it-admin") -> dict:
    return {
        "body": json.dumps(body),
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": ACTOR_ID,
                    "cognito:groups": group,
                }
            }
        },
    }


def _valid_body(**overrides) -> dict:
    base = {
        "scan_job_id": SCAN_JOB_ID,
        "procurement_id": "PROC-001",
        "approved_budget": 5000.0,
        "requestor": ACTOR_ID,
        "category": "LAPTOP",
        "invoice_number": "INV-001",
        "vendor": "Dell Technologies",
        "purchase_date": "2026-03-01",
        "brand": "Dell",
        "model_name": "Latitude 5540",
        "cost": 1299.0,
        "serial_number": "SN-UNIQUE-001",
    }
    base.update(overrides)
    return base


def _seed_scan_and_session(table, serial_number=None):
    table.put_item(
        Item={
            "PK": f"SCAN#{SCAN_JOB_ID}",
            "SK": "METADATA",
            "ScanJobID": SCAN_JOB_ID,
            "UploadSessionID": SESSION_ID,
            "Status": "COMPLETED",
            "CreatedAt": "2026-01-01T00:00:00+00:00",
        }
    )
    table.put_item(
        Item={
            "PK": f"SESSION#{SESSION_ID}",
            "SK": "METADATA",
            "UploadSessionID": SESSION_ID,
            "InvoiceS3Key": "uploads/session-create-001/invoice/inv.pdf",
            "GadgetPhotoS3Keys": ["uploads/session-create-001/gadget_photo/p1.jpg"],
            "CreatedAt": "2026-01-01T00:00:00+00:00",
            "TTL": 9999999999,
        }
    )


def _seed_category(table, category_name="LAPTOP"):
    """Seed a category record so CreateAsset's DynamoDB validation passes."""
    table.put_item(
        Item={
            "PK": f"CATEGORY#{category_name}",
            "SK": "METADATA",
            "CategoryID": category_name,
            "CategoryName": category_name,
            "CreatedAt": "2026-01-01T00:00:00+00:00",
            "CategoryEntityType": "CATEGORY",
            "CategoryNameIndexPK": f"CATEGORY_NAME#{category_name}",
        }
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_creates_asset_returns_201(aws_mocks):
    _seed_scan_and_session(aws_mocks["table"])
    _seed_category(aws_mocks["table"])

    import lambda_function

    result = lambda_function.lambda_handler(_make_event(_valid_body()), _CTX)

    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert "asset_id" in body
    assert body["status"] == "ASSET_PENDING_APPROVAL"


def test_asset_id_format(aws_mocks):
    _seed_scan_and_session(aws_mocks["table"])
    _seed_category(aws_mocks["table"])

    import lambda_function

    result = lambda_function.lambda_handler(_make_event(_valid_body()), _CTX)

    body = json.loads(result["body"])
    asset_id = body["asset_id"]
    # Format: LAPTOP-2026-001
    parts = asset_id.split("-")
    assert parts[0] == "LAPTOP"
    assert len(parts[1]) == 4  # year
    assert len(parts[2]) == 3  # zero-padded counter


@pytest.mark.parametrize(
    "count,expected_suffix",
    [
        (1, "001"),
        (42, "042"),
        (100, "100"),
    ],
)
def test_asset_id_zero_padding(aws_mocks, count, expected_suffix):
    """Counter value is zero-padded to 3 digits."""
    table = aws_mocks["table"]
    _seed_scan_and_session(table)
    _seed_category(table)

    # Pre-seed counter so next increment gives the desired count
    from datetime import datetime, timezone

    year = datetime.now(timezone.utc).year
    table.put_item(
        Item={
            "PK": f"COUNTER#LAPTOP#{year}",
            "SK": "METADATA",
            "Count": count - 1,
        }
    )

    import lambda_function

    result = lambda_function.lambda_handler(_make_event(_valid_body()), _CTX)

    body = json.loads(result["body"])
    assert body["asset_id"].endswith(f"-{expected_suffix}")


def test_asset_written_to_dynamodb(aws_mocks):
    table = aws_mocks["table"]
    _seed_scan_and_session(table)
    _seed_category(table)

    import lambda_function

    result = lambda_function.lambda_handler(_make_event(_valid_body()), _CTX)

    body = json.loads(result["body"])
    asset_id = body["asset_id"]

    item = table.get_item(Key={"PK": f"ASSET#{asset_id}", "SK": "METADATA"})["Item"]
    assert item["Status"] == "ASSET_PENDING_APPROVAL"
    assert item["StatusIndexPK"] == "STATUS#ASSET_PENDING_APPROVAL"
    assert item["StatusIndexSK"] == f"ASSET#{asset_id}"
    assert item["Brand"] == "Dell"
    assert item["Vendor"] == "Dell Technologies"


def test_serial_number_gsi_keys_set(aws_mocks):
    table = aws_mocks["table"]
    _seed_scan_and_session(table)
    _seed_category(table)

    import lambda_function

    result = lambda_function.lambda_handler(
        _make_event(_valid_body(serial_number="SN-GSI-TEST")), _CTX
    )

    body = json.loads(result["body"])
    item = table.get_item(Key={"PK": f"ASSET#{body['asset_id']}", "SK": "METADATA"})[
        "Item"
    ]
    assert item["SerialNumberIndexPK"] == "SERIAL#SN-GSI-TEST"
    assert item["SerialNumberIndexSK"] == "METADATA"


def test_audit_log_written(aws_mocks):
    table = aws_mocks["table"]
    _seed_scan_and_session(table)
    _seed_category(table)

    import lambda_function

    result = lambda_function.lambda_handler(_make_event(_valid_body()), _CTX)

    body = json.loads(result["body"])
    asset_id = body["asset_id"]

    # Query audit log entries
    response = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :prefix)",
        ExpressionAttributeValues={
            ":pk": f"ASSET#{asset_id}",
            ":prefix": "LOG#",
        },
    )
    logs = response["Items"]
    assert len(logs) == 1
    log = logs[0]
    assert log["Phase"] == "ASSET_CREATION"
    assert log["PreviousStatus"] == ""
    assert log["NewStatus"] == "ASSET_PENDING_APPROVAL"
    assert log["ActorID"] == ACTOR_ID


# ---------------------------------------------------------------------------
# Serial number uniqueness
# ---------------------------------------------------------------------------


def test_duplicate_serial_number_returns_409(aws_mocks):
    table = aws_mocks["table"]
    _seed_scan_and_session(table)
    _seed_category(table)

    # Seed existing asset with same serial number
    table.put_item(
        Item={
            "PK": "ASSET#LAPTOP-2026-000",
            "SK": "METADATA",
            "SerialNumberIndexPK": "SERIAL#SN-UNIQUE-001",
            "SerialNumberIndexSK": "METADATA",
            "Status": "IN_STOCK",
            "EntityType": "ASSET",
        }
    )

    import lambda_function

    result = lambda_function.lambda_handler(_make_event(_valid_body()), _CTX)

    assert result["statusCode"] == 409
    assert "serial number already exists" in json.loads(result["body"])["message"]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "missing_field",
    [
        "invoice_number",
        "vendor",
        "purchase_date",
        "brand",
        "model_name",
        "cost",
        "category",
    ],
)
def test_missing_required_field_returns_400(aws_mocks, missing_field):
    _seed_scan_and_session(aws_mocks["table"])
    _seed_category(aws_mocks["table"])
    body = _valid_body()
    del body[missing_field]

    import lambda_function

    result = lambda_function.lambda_handler(_make_event(body), _CTX)

    assert result["statusCode"] == 400


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_non_it_admin_returns_403(aws_mocks):
    _seed_scan_and_session(aws_mocks["table"])

    import lambda_function

    result = lambda_function.lambda_handler(
        _make_event(_valid_body(), group="employee"), _CTX
    )

    assert result["statusCode"] == 403
