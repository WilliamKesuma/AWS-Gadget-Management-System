"""Unit tests for the MarkNotificationRead Lambda.

Tests cover marking unread → read, 404 for non-existent, 404 for another
user's notification, and response field completeness.
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone

import boto3
import pytest
from moto import mock_aws

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
_MARK_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        os.pardir,
        os.pardir,
        "services",
        "lambdas",
        "functions",
        "MarkNotificationRead",
    )
)
_FUNCS_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        os.pardir,
        os.pardir,
        "services",
        "lambdas",
        "functions",
    )
)


def _import_handler():
    """Import the MarkNotificationRead lambda_handler inside a mock context.

    Temporarily adjusts sys.path, then restores it.
    """
    saved_path = sys.path[:]
    sys.path = [p for p in sys.path if not p.startswith(_FUNCS_ROOT)]
    sys.path.insert(0, _MARK_DIR)

    for mod_name in ("lambda_function", "model"):
        sys.modules.pop(mod_name, None)

    from lambda_function import lambda_handler

    sys.path = saved_path
    return lambda_handler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_A = "user-mark-aaa"
USER_B = "user-mark-bbb"


class _FakeLambdaContext:
    function_name = "test-mark-notification-read"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:ap-southeast-1:123456789012:function:test"
    aws_request_id = "test-request-id"


_CTX = _FakeLambdaContext()


def _make_event(user_id: str, notification_id: str, group: str = "employee") -> dict:
    return {
        "httpMethod": "PATCH",
        "path": f"/notifications/{notification_id}",
        "headers": {"Content-Type": "application/json"},
        "body": None,
        "queryStringParameters": None,
        "pathParameters": {"notification_id": notification_id},
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": user_id,
                    "email": f"{user_id}@example.com",
                    "cognito:groups": group,
                }
            }
        },
    }


def _seed_notification(
    table,
    user_id: str,
    notification_id: str | None = None,
    is_read: bool = False,
) -> str:
    nid = notification_id or str(uuid.uuid4())
    timestamp = "2024-08-15T10:00:00+00:00"
    created_epoch = int(datetime.fromisoformat(timestamp).timestamp())
    expires_at = created_epoch + 7_776_000

    table.put_item(
        Item={
            "PK": f"USER#{user_id}",
            "SK": f"NOTIFICATION#{timestamp}#{nid}",
            "NotificationType": "ASSET_PENDING_APPROVAL",
            "Title": "Asset Pending Approval",
            "Message": "Asset asset-001 requires your approval.",
            "ReferenceID": "asset-001",
            "ReferenceType": "ASSET",
            "IsRead": is_read,
            "CreatedAt": timestamp,
            "ExpiresAt": expires_at,
            "TTL": expires_at,
            "EntityType": "NOTIFICATION",
        }
    )
    return nid


# ---------------------------------------------------------------------------
# Property 11: Mark unread notification sets IsRead=true
# ---------------------------------------------------------------------------


def test_mark_unread_notification_sets_is_read_true(mock_dynamodb):
    """Property 11: Marking an unread notification sets IsRead=true."""
    table = mock_dynamodb
    handler = _import_handler()
    nid = _seed_notification(table, USER_A, is_read=False)

    response = handler(_make_event(USER_A, nid), _CTX)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["is_read"] is True
    assert body["notification_id"] == nid


# ---------------------------------------------------------------------------
# Property 11: 404 for non-existent notification
# ---------------------------------------------------------------------------


def test_nonexistent_notification_returns_404(mock_dynamodb):
    """Property 11: PATCH with a random UUID returns 404."""
    handler = _import_handler()

    response = handler(_make_event(USER_A, str(uuid.uuid4())), _CTX)

    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert "not found" in body["message"].lower()


# ---------------------------------------------------------------------------
# Property 11: 404 for another user's notification
# ---------------------------------------------------------------------------


def test_other_users_notification_returns_404(mock_dynamodb):
    """Property 11: Notification belonging to user A returns 404 when user B calls PATCH."""
    table = mock_dynamodb
    handler = _import_handler()
    nid = _seed_notification(table, USER_A, is_read=False)

    response = handler(_make_event(USER_B, nid), _CTX)

    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert "not found" in body["message"].lower()


# ---------------------------------------------------------------------------
# Property 11: Response field completeness
# ---------------------------------------------------------------------------


def test_response_contains_all_expected_fields(mock_dynamodb):
    """Property 11: Response contains all expected fields."""
    table = mock_dynamodb
    handler = _import_handler()
    nid = _seed_notification(table, USER_A, is_read=False)

    response = handler(_make_event(USER_A, nid), _CTX)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])

    expected_fields = {
        "notification_id",
        "notification_type",
        "title",
        "message",
        "reference_id",
        "reference_type",
        "is_read",
        "created_at",
    }
    assert expected_fields.issubset(set(body.keys()))
    assert body["notification_type"] == "ASSET_PENDING_APPROVAL"
    assert body["title"] == "Asset Pending Approval"
    assert body["reference_id"] == "asset-001"
    assert body["reference_type"] == "ASSET"
