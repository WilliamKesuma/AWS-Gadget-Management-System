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
        "ApproveAsset",
    ),
)

ASSET_ID = "LAPTOP-2026-001"
ACTOR_ID = "mgmt-user-id-001"


class _FakeLambdaContext:
    """Minimal Lambda context for aws_lambda_powertools decorators."""

    function_name = "test-approve-asset"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:ap-southeast-1:123456789012:function:test"
    aws_request_id = "test-request-id"


_CTX = _FakeLambdaContext()


def _make_event(
    body: dict, asset_id: str = ASSET_ID, group: str = "management"
) -> dict:
    return {
        "body": json.dumps(body),
        "pathParameters": {"asset_id": asset_id},
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": ACTOR_ID,
                    "cognito:groups": group,
                }
            }
        },
    }


def _seed_pending_asset(
    table, asset_id: str = ASSET_ID, status: str = "ASSET_PENDING_APPROVAL"
):
    table.put_item(
        Item={
            "PK": f"ASSET#{asset_id}",
            "SK": "METADATA",
            "ProcurementID": "PROC-001",
            "ApprovedBudget": "5000",
            "Requestor": "admin-user-id-1234",
            "InvoiceNumber": "INV-001",
            "Vendor": "Dell",
            "PurchaseDate": "2026-03-01",
            "Brand": "Dell",
            "Model": "Latitude 5540",
            "Cost": "1299",
            "Status": status,
            "EntityType": "ASSET",
            "StatusIndexPK": f"STATUS#{status}",
            "StatusIndexSK": f"ASSET#{asset_id}",
        }
    )


# ---------------------------------------------------------------------------
# APPROVE
# ---------------------------------------------------------------------------


def test_approve_sets_in_stock(aws_mocks):
    _seed_pending_asset(aws_mocks["table"])

    import lambda_function

    result = lambda_function.lambda_handler(_make_event({"action": "APPROVE"}), _CTX)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["status"] == "IN_STOCK"
    assert body["asset_id"] == ASSET_ID


def test_approve_updates_dynamodb_status(aws_mocks):
    table = aws_mocks["table"]
    _seed_pending_asset(table)

    import lambda_function

    lambda_function.lambda_handler(_make_event({"action": "APPROVE"}), _CTX)

    item = table.get_item(Key={"PK": f"ASSET#{ASSET_ID}", "SK": "METADATA"})["Item"]
    assert item["Status"] == "IN_STOCK"
    assert item["StatusIndexPK"] == "STATUS#IN_STOCK"
    assert item["StatusIndexSK"] == f"ASSET#{ASSET_ID}"


def test_approve_with_remarks(aws_mocks):
    table = aws_mocks["table"]
    _seed_pending_asset(table)

    import lambda_function

    lambda_function.lambda_handler(
        _make_event({"action": "APPROVE", "remarks": "Looks good"}), _CTX
    )

    item = table.get_item(Key={"PK": f"ASSET#{ASSET_ID}", "SK": "METADATA"})["Item"]
    assert item.get("Remarks") == "Looks good"


# ---------------------------------------------------------------------------
# REJECT
# ---------------------------------------------------------------------------


def test_reject_sets_asset_rejected(aws_mocks):
    _seed_pending_asset(aws_mocks["table"])

    import lambda_function

    result = lambda_function.lambda_handler(
        _make_event({"action": "REJECT", "rejection_reason": "Budget exceeded"}), {}
    )

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["status"] == "ASSET_REJECTED"


def test_reject_stores_rejection_reason(aws_mocks):
    table = aws_mocks["table"]
    _seed_pending_asset(table)

    import lambda_function

    lambda_function.lambda_handler(
        _make_event({"action": "REJECT", "rejection_reason": "Budget exceeded"}), {}
    )

    item = table.get_item(Key={"PK": f"ASSET#{ASSET_ID}", "SK": "METADATA"})["Item"]
    assert item["Status"] == "ASSET_REJECTED"
    assert item["RejectionReason"] == "Budget exceeded"


def test_reject_without_reason_returns_400(aws_mocks):
    _seed_pending_asset(aws_mocks["table"])

    import lambda_function

    result = lambda_function.lambda_handler(_make_event({"action": "REJECT"}), {})

    assert result["statusCode"] == 400
    assert "Rejection reason is required" in json.loads(result["body"])["message"]


def test_reject_with_empty_reason_returns_400(aws_mocks):
    _seed_pending_asset(aws_mocks["table"])

    import lambda_function

    result = lambda_function.lambda_handler(
        _make_event({"action": "REJECT", "rejection_reason": "   "}), {}
    )

    assert result["statusCode"] == 400


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


def test_audit_log_written_on_approve(aws_mocks):
    table = aws_mocks["table"]
    _seed_pending_asset(table)

    import lambda_function

    lambda_function.lambda_handler(_make_event({"action": "APPROVE"}), {})

    response = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :prefix)",
        ExpressionAttributeValues={
            ":pk": f"ASSET#{ASSET_ID}",
            ":prefix": "LOG#",
        },
    )
    logs = response["Items"]
    assert len(logs) == 1
    log = logs[0]
    assert log["Phase"] == "ASSET_APPROVAL"
    assert log["PreviousStatus"] == "ASSET_PENDING_APPROVAL"
    assert log["NewStatus"] == "IN_STOCK"
    assert log["ActorID"] == ACTOR_ID


def test_audit_log_written_on_reject(aws_mocks):
    table = aws_mocks["table"]
    _seed_pending_asset(table)

    import lambda_function

    lambda_function.lambda_handler(
        _make_event({"action": "REJECT", "rejection_reason": "Not approved"}), {}
    )

    response = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :prefix)",
        ExpressionAttributeValues={
            ":pk": f"ASSET#{ASSET_ID}",
            ":prefix": "LOG#",
        },
    )
    logs = response["Items"]
    assert len(logs) == 1
    assert logs[0]["NewStatus"] == "ASSET_REJECTED"
    assert logs[0]["RejectionReason"] == "Not approved"


# ---------------------------------------------------------------------------
# Wrong status / not found
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", ["IN_STOCK", "ASSET_REJECTED", "ASSIGNED"])
def test_wrong_status_returns_409(aws_mocks, status):
    _seed_pending_asset(aws_mocks["table"], status=status)

    import lambda_function

    result = lambda_function.lambda_handler(_make_event({"action": "APPROVE"}), {})

    assert result["statusCode"] == 409
    assert "pending approval" in json.loads(result["body"])["message"]


def test_nonexistent_asset_returns_404(aws_mocks):
    import lambda_function

    result = lambda_function.lambda_handler(
        _make_event({"action": "APPROVE"}, asset_id="LAPTOP-2026-999"), {}
    )

    assert result["statusCode"] == 404
    assert "Asset not found" in json.loads(result["body"])["message"]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_non_management_returns_403(aws_mocks):
    _seed_pending_asset(aws_mocks["table"])

    import lambda_function

    result = lambda_function.lambda_handler(
        _make_event({"action": "APPROVE"}, group="it-admin"), {}
    )

    assert result["statusCode"] == 403
