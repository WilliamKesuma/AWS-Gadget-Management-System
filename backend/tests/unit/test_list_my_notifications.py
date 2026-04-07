"""Unit tests for the ListMyNotifications Lambda.

Tests cover user isolation, sort order, pagination, is_read filter,
unread_count accuracy, empty list, and invalid pagination parameters.
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

import boto3
import pytest
from moto import mock_aws

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
_LIST_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        os.pardir,
        os.pardir,
        "services",
        "lambdas",
        "functions",
        "ListMyNotifications",
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
    """Import the ListMyNotifications lambda_handler inside a mock context.

    Temporarily adjusts sys.path, then restores it to avoid polluting
    other test modules.
    """
    saved_path = sys.path[:]
    sys.path = [p for p in sys.path if not p.startswith(_FUNCS_ROOT)]
    sys.path.insert(0, _LIST_DIR)

    for mod_name in ("lambda_function", "model"):
        sys.modules.pop(mod_name, None)

    from lambda_function import lambda_handler

    sys.path = saved_path
    return lambda_handler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_A = "user-aaa-111"
USER_B = "user-bbb-222"


class _FakeLambdaContext:
    function_name = "test-list-my-notifications"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:ap-southeast-1:123456789012:function:test"
    aws_request_id = "test-request-id"


_CTX = _FakeLambdaContext()


def _make_event(
    user_id: str = USER_A,
    query_params: dict | None = None,
    group: str = "employee",
) -> dict:
    return {
        "httpMethod": "GET",
        "path": "/notifications",
        "headers": {"Content-Type": "application/json"},
        "body": None,
        "queryStringParameters": query_params,
        "pathParameters": None,
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
    timestamp: str,
    is_read: bool = False,
    notification_type: str = "ASSET_PENDING_APPROVAL",
) -> str:
    notification_id = str(uuid.uuid4())
    created_epoch = int(datetime.fromisoformat(timestamp).timestamp())
    expires_at = created_epoch + 7_776_000

    table.put_item(
        Item={
            "PK": f"USER#{user_id}",
            "SK": f"NOTIFICATION#{timestamp}#{notification_id}",
            "NotificationType": notification_type,
            "Title": "Test Notification",
            "Message": f"Test message for {notification_id}",
            "ReferenceID": "asset-001",
            "ReferenceType": "ASSET",
            "IsRead": is_read,
            "CreatedAt": timestamp,
            "ExpiresAt": expires_at,
            "TTL": expires_at,
            "EntityType": "NOTIFICATION",
        }
    )
    return notification_id


# ---------------------------------------------------------------------------
# Property 7: User notification isolation
# ---------------------------------------------------------------------------


def test_list_returns_only_caller_notifications(mock_dynamodb):
    """Property 7: GET returns only the caller's notifications."""
    table = mock_dynamodb
    handler = _import_handler()

    _seed_notification(table, USER_A, "2024-08-01T10:00:00+00:00")
    _seed_notification(table, USER_A, "2024-08-02T10:00:00+00:00")
    _seed_notification(table, USER_B, "2024-08-03T10:00:00+00:00")

    response = handler(_make_event(USER_A, {"page": "1", "page_size": "20"}), _CTX)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["total_items"] == 2


# ---------------------------------------------------------------------------
# Property 7: Descending sort order
# ---------------------------------------------------------------------------


def test_list_returns_newest_first(mock_dynamodb):
    """Property 7: Notifications come back newest first."""
    table = mock_dynamodb
    handler = _import_handler()

    for ts in (
        "2024-08-01T10:00:00+00:00",
        "2024-08-02T10:00:00+00:00",
        "2024-08-03T10:00:00+00:00",
    ):
        _seed_notification(table, USER_A, ts)

    response = handler(_make_event(USER_A, {"page": "1", "page_size": "20"}), _CTX)
    body = json.loads(response["body"])
    items = body["items"]
    assert len(items) == 3

    timestamps = [item["created_at"] for item in items]
    assert timestamps == sorted(timestamps, reverse=True)


# ---------------------------------------------------------------------------
# Property 8: Pagination correctness
# ---------------------------------------------------------------------------


def test_pagination_page_2_of_3(mock_dynamodb):
    """Property 8: Seed 7 notifications, page=2 page_size=3 returns correct slice."""
    table = mock_dynamodb
    handler = _import_handler()

    base = datetime(2024, 8, 1, tzinfo=timezone.utc)
    for i in range(7):
        ts = (base + timedelta(hours=i)).isoformat()
        _seed_notification(table, USER_A, ts)

    response = handler(_make_event(USER_A, {"page": "2", "page_size": "3"}), _CTX)
    body = json.loads(response["body"])

    assert body["total_items"] == 7
    assert body["total_pages"] == 3
    assert body["current_page"] == 2
    assert body["count"] == 3


# ---------------------------------------------------------------------------
# Property 9: is_read filter
# ---------------------------------------------------------------------------


def test_is_read_filter_false(mock_dynamodb):
    """Property 9: is_read=false returns only unread notifications."""
    table = mock_dynamodb
    handler = _import_handler()

    _seed_notification(table, USER_A, "2024-08-01T10:00:00+00:00", is_read=False)
    _seed_notification(table, USER_A, "2024-08-02T10:00:00+00:00", is_read=True)
    _seed_notification(table, USER_A, "2024-08-03T10:00:00+00:00", is_read=False)

    response = handler(
        _make_event(USER_A, {"page": "1", "page_size": "20", "is_read": "false"}), _CTX
    )
    body = json.loads(response["body"])

    assert body["total_items"] == 2
    for item in body["items"]:
        assert item["is_read"] is False


# ---------------------------------------------------------------------------
# Property 10: Unread count accuracy
# ---------------------------------------------------------------------------


def test_unread_count_reflects_total_unread(mock_dynamodb):
    """Property 10: unread_count reflects total unread regardless of page or filter."""
    table = mock_dynamodb
    handler = _import_handler()

    _seed_notification(table, USER_A, "2024-08-01T10:00:00+00:00", is_read=False)
    _seed_notification(table, USER_A, "2024-08-02T10:00:00+00:00", is_read=False)
    _seed_notification(table, USER_A, "2024-08-03T10:00:00+00:00", is_read=True)
    _seed_notification(table, USER_A, "2024-08-04T10:00:00+00:00", is_read=False)
    _seed_notification(table, USER_A, "2024-08-05T10:00:00+00:00", is_read=True)

    response = handler(_make_event(USER_A, {"page": "1", "page_size": "2"}), _CTX)
    body = json.loads(response["body"])
    assert body["unread_count"] == 3

    response2 = handler(
        _make_event(USER_A, {"page": "1", "page_size": "20", "is_read": "true"}), _CTX
    )
    body2 = json.loads(response2["body"])
    assert body2["unread_count"] == 3


# ---------------------------------------------------------------------------
# Property 7: Empty list
# ---------------------------------------------------------------------------


def test_empty_list_returns_zero(mock_dynamodb):
    """Property 7: Empty items with unread_count=0 for user with no notifications."""
    handler = _import_handler()

    response = handler(_make_event(USER_A, {"page": "1", "page_size": "20"}), _CTX)
    body = json.loads(response["body"])

    assert body["items"] == []
    assert body["total_items"] == 0
    assert body["unread_count"] == 0


# ---------------------------------------------------------------------------
# Property 8: Invalid pagination parameters
# ---------------------------------------------------------------------------


def test_invalid_page_returns_400(mock_dynamodb):
    """Property 8: Non-integer page value returns 400."""
    handler = _import_handler()

    response = handler(_make_event(USER_A, {"page": "abc", "page_size": "20"}), _CTX)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert (
        "pagination" in body["message"].lower() or "invalid" in body["message"].lower()
    )
