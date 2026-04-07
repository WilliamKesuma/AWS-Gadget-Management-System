"""Unit tests for the NotificationProcessor Lambda.

Tests cover stream event processing, rule matching, recipient resolution,
notification record creation, error isolation, and TTL calculation.
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
_PROCESSOR_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        os.pardir,
        os.pardir,
        "services",
        "lambdas",
        "functions",
        "NotificationProcessor",
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


def _import_processor():
    """Import the NotificationProcessor lambda_function inside a mock context.

    Temporarily adjusts sys.path so that ``import lambda_function`` and
    ``import model`` resolve to the NotificationProcessor directory, then
    restores the original sys.path to avoid polluting other test modules.
    """
    saved_path = sys.path[:]
    # Remove any Lambda function dirs, then prepend ours
    sys.path = [p for p in sys.path if not p.startswith(_FUNCS_ROOT)]
    sys.path.insert(0, _PROCESSOR_DIR)

    # Evict cached modules so they reimport from the correct directory
    for mod_name in ("lambda_function", "model", "rules"):
        sys.modules.pop(mod_name, None)

    from lambda_function import (
        find_matching_rules,
        resolve_recipients,
        create_notifications,
        _deserialize_image,
        _get_entity_prefix,
        _extract_reference_id,
        lambda_handler,
    )
    from model import StreamRecordData

    # Restore original sys.path
    sys.path = saved_path

    return {
        "find_matching_rules": find_matching_rules,
        "resolve_recipients": resolve_recipients,
        "create_notifications": create_notifications,
        "_deserialize_image": _deserialize_image,
        "_get_entity_prefix": _get_entity_prefix,
        "_extract_reference_id": _extract_reference_id,
        "lambda_handler": lambda_handler,
        "StreamRecordData": StreamRecordData,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TABLE_NAME = "gms-dev-assets"
REGION = "ap-southeast-1"


class _FakeLambdaContext:
    """Minimal Lambda context for aws_lambda_powertools decorators."""

    function_name = "test-notification-processor"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:ap-southeast-1:123456789012:function:test"
    aws_request_id = "test-request-id"


def _build_stream_event(records: list[dict]) -> dict:
    return {"Records": records}


def _build_stream_record(
    event_name: str,
    new_image: dict | None = None,
    old_image: dict | None = None,
) -> dict:
    record = {"eventName": event_name, "dynamodb": {}}
    if new_image is not None:
        record["dynamodb"]["NewImage"] = new_image
    if old_image is not None:
        record["dynamodb"]["OldImage"] = old_image
    return record


def _ddb_s(value: str) -> dict:
    return {"S": value}


def _seed_users(table, role: str, count: int, active: bool = True) -> list[str]:
    """Seed user records and return their user IDs."""
    user_ids = []
    for i in range(count):
        uid = f"{role}-user-{i}"
        table.put_item(
            Item={
                "PK": f"USER#{uid}",
                "SK": "METADATA",
                "UserID": uid,
                "Fullname": f"Test {role.title()} {i}",
                "Email": f"{role}{i}@example.com",
                "Role": role,
                "Status": "active" if active else "inactive",
                "CreatedAt": "2024-01-01T00:00:00+00:00",
                "EntityType": "USER",
            }
        )
        user_ids.append(uid)
    return user_ids


# ---------------------------------------------------------------------------
# Property 1: MODIFY event status change detection
# ---------------------------------------------------------------------------


def test_modify_event_detects_status_change_asset_pending_approval(mock_dynamodb):
    """Property 1: MODIFY event with Status change to ASSET_PENDING_APPROVAL
    matches the correct notification rule."""
    mod = _import_processor()

    record_data = mod["StreamRecordData"](
        event_name="MODIFY",
        entity_prefix="METADATA",
        old_image={"PK": "ASSET#a1", "SK": "METADATA", "Status": "IN_STOCK"},
        new_image={
            "PK": "ASSET#a1",
            "SK": "METADATA",
            "Status": "ASSET_PENDING_APPROVAL",
        },
    )
    matched = mod["find_matching_rules"](record_data)
    assert len(matched) >= 1
    types = [r["notification_type"] for r in matched]
    assert "ASSET_PENDING_APPROVAL" in types


def test_modify_event_no_status_change_yields_no_match(mock_dynamodb):
    """Property 1: MODIFY event with same Status in OldImage/NewImage yields no match."""
    mod = _import_processor()

    record_data = mod["StreamRecordData"](
        event_name="MODIFY",
        entity_prefix="METADATA",
        old_image={"PK": "ASSET#a1", "SK": "METADATA", "Status": "IN_STOCK"},
        new_image={"PK": "ASSET#a1", "SK": "METADATA", "Status": "IN_STOCK"},
    )
    matched = mod["find_matching_rules"](record_data)
    assert len(matched) == 0


# ---------------------------------------------------------------------------
# Property 2: INSERT event rule evaluation
# ---------------------------------------------------------------------------


def test_insert_handover_matches_handover_form_ready(mock_dynamodb):
    """Property 2: INSERT event for a HANDOVER# record matches HANDOVER_FORM_READY."""
    mod = _import_processor()

    record_data = mod["StreamRecordData"](
        event_name="INSERT",
        entity_prefix="HANDOVER#",
        old_image=None,
        new_image={
            "PK": "ASSET#a1",
            "SK": "HANDOVER#2024-07-01T10:00:00+00:00",
            "EmployeeID": "emp-001",
        },
    )
    matched = mod["find_matching_rules"](record_data)
    assert len(matched) == 1
    assert matched[0]["notification_type"] == "HANDOVER_FORM_READY"


# ---------------------------------------------------------------------------
# Property 3: Error isolation in batch processing
# ---------------------------------------------------------------------------


def test_error_isolation_bad_record_does_not_block_good_record(mock_dynamodb):
    """Property 3: One bad record in a batch doesn't prevent processing of good records."""
    table = mock_dynamodb
    mod = _import_processor()

    _seed_users(table, "management", 1)

    bad_record = {"eventName": "MODIFY"}
    good_record = _build_stream_record(
        "MODIFY",
        old_image={
            "PK": _ddb_s("ASSET#a1"),
            "SK": _ddb_s("METADATA"),
            "Status": _ddb_s("IN_STOCK"),
        },
        new_image={
            "PK": _ddb_s("ASSET#a1"),
            "SK": _ddb_s("METADATA"),
            "Status": _ddb_s("ASSET_PENDING_APPROVAL"),
        },
    )

    event = _build_stream_event([bad_record, good_record])
    mod["lambda_handler"](event, _FakeLambdaContext())

    from boto3.dynamodb.conditions import Key

    response = table.query(
        KeyConditionExpression=Key("PK").eq("USER#management-user-0")
    )
    notifications = [
        i for i in response["Items"] if i["SK"].startswith("NOTIFICATION#")
    ]
    assert len(notifications) >= 1


# ---------------------------------------------------------------------------
# Property 4: Rule matching for all roles
# ---------------------------------------------------------------------------


def test_rule_matching_management_role(mock_dynamodb):
    """Property 4: Management rules match for ASSET_PENDING_APPROVAL."""
    mod = _import_processor()

    record_data = mod["StreamRecordData"](
        event_name="MODIFY",
        entity_prefix="METADATA",
        old_image={"Status": "IN_STOCK"},
        new_image={"Status": "ASSET_PENDING_APPROVAL"},
    )
    matched = mod["find_matching_rules"](record_data)
    types = [r["notification_type"] for r in matched]
    assert "ASSET_PENDING_APPROVAL" in types
    mgmt_rules = [
        r for r in matched if r["notification_type"] == "ASSET_PENDING_APPROVAL"
    ]
    assert mgmt_rules[0]["target_role"] == "management"


def test_rule_matching_it_admin_role(mock_dynamodb):
    """Property 4: IT admin rules match for ASSET_APPROVED."""
    mod = _import_processor()

    record_data = mod["StreamRecordData"](
        event_name="MODIFY",
        entity_prefix="METADATA",
        old_image={"Status": "ASSET_PENDING_APPROVAL"},
        new_image={"Status": "IN_STOCK"},
    )
    matched = mod["find_matching_rules"](record_data)
    types = [r["notification_type"] for r in matched]
    assert "ASSET_APPROVED" in types
    it_rules = [r for r in matched if r["notification_type"] == "ASSET_APPROVED"]
    assert it_rules[0]["target_role"] == "it-admin"


def test_rule_matching_employee_role(mock_dynamodb):
    """Property 4: Employee rules match for NEW_ASSET_ASSIGNED."""
    mod = _import_processor()

    record_data = mod["StreamRecordData"](
        event_name="MODIFY",
        entity_prefix="METADATA",
        old_image={"Status": "IN_STOCK"},
        new_image={"Status": "ASSIGNED", "EmployeeAssetIndexPK": "EMPLOYEE#emp-001"},
    )
    matched = mod["find_matching_rules"](record_data)
    types = [r["notification_type"] for r in matched]
    assert "NEW_ASSET_ASSIGNED" in types
    emp_rules = [r for r in matched if r["notification_type"] == "NEW_ASSET_ASSIGNED"]
    assert emp_rules[0]["target_role"] is None
    assert emp_rules[0]["recipient_field"] == "EmployeeAssetIndexPK"


def test_rule_matching_finance_role(mock_dynamodb):
    """Property 4: Finance rules match for ASSET_DISPOSED_WRITEOFF."""
    mod = _import_processor()

    record_data = mod["StreamRecordData"](
        event_name="MODIFY",
        entity_prefix="METADATA",
        old_image={"Status": "DISPOSAL_PENDING"},
        new_image={"Status": "DISPOSED"},
    )
    matched = mod["find_matching_rules"](record_data)
    types = [r["notification_type"] for r in matched]
    assert "ASSET_DISPOSED_WRITEOFF" in types
    fin_rules = [
        r for r in matched if r["notification_type"] == "ASSET_DISPOSED_WRITEOFF"
    ]
    assert fin_rules[0]["target_role"] == "finance"


# ---------------------------------------------------------------------------
# Property 4: Recipient resolution — role-based
# ---------------------------------------------------------------------------


def test_resolve_recipients_role_based(mock_dynamodb):
    """Property 4: Role-based resolution returns only active users with the target role."""
    table = mock_dynamodb
    mod = _import_processor()

    user_ids = _seed_users(table, "management", 2)
    table.put_item(
        Item={
            "PK": "USER#mgmt-inactive",
            "SK": "METADATA",
            "UserID": "mgmt-inactive",
            "Fullname": "Inactive Manager",
            "Email": "inactive@example.com",
            "Role": "management",
            "Status": "inactive",
            "CreatedAt": "2024-01-01T00:00:00+00:00",
            "EntityType": "USER",
        }
    )

    rule = {
        "target_role": "management",
        "recipient_field": None,
        "notification_type": "ASSET_PENDING_APPROVAL",
    }
    recipients = mod["resolve_recipients"](rule, {})
    assert set(recipients) == set(user_ids)
    assert "mgmt-inactive" not in recipients


# ---------------------------------------------------------------------------
# Property 4: Recipient resolution — user-specific
# ---------------------------------------------------------------------------


def test_resolve_recipients_user_specific_employee_id(mock_dynamodb):
    """Property 4: User-specific resolution extracts EmployeeID."""
    mod = _import_processor()

    rule = {
        "target_role": None,
        "recipient_field": "EmployeeID",
        "notification_type": "HANDOVER_FORM_READY",
    }
    recipients = mod["resolve_recipients"](rule, {"EmployeeID": "emp-001"})
    assert recipients == ["emp-001"]


def test_resolve_recipients_user_specific_strips_employee_prefix(mock_dynamodb):
    """Property 4: User-specific resolution strips EMPLOYEE# prefix."""
    mod = _import_processor()

    rule = {
        "target_role": None,
        "recipient_field": "EmployeeAssetIndexPK",
        "notification_type": "NEW_ASSET_ASSIGNED",
    }
    recipients = mod["resolve_recipients"](
        rule, {"EmployeeAssetIndexPK": "EMPLOYEE#emp-002"}
    )
    assert recipients == ["emp-002"]


# ---------------------------------------------------------------------------
# Property 5: Notification record completeness
# ---------------------------------------------------------------------------


def test_notification_record_completeness(mock_dynamodb):
    """Property 5: Created notification records have all required fields and valid UUID v4."""
    table = mock_dynamodb
    mod = _import_processor()

    rule = {
        "notification_type": "ASSET_PENDING_APPROVAL",
        "title": "Asset Pending Approval",
        "message_template": "Asset {reference_id} requires your approval.",
        "reference_type": "ASSET",
    }
    mod["create_notifications"](["user-001"], rule, "asset-123")

    from boto3.dynamodb.conditions import Key

    response = table.query(KeyConditionExpression=Key("PK").eq("USER#user-001"))
    notifications = [
        i for i in response["Items"] if i["SK"].startswith("NOTIFICATION#")
    ]
    assert len(notifications) == 1
    notif = notifications[0]

    assert notif["PK"] == "USER#user-001"
    assert notif["SK"].startswith("NOTIFICATION#")
    assert notif["NotificationType"] == "ASSET_PENDING_APPROVAL"
    assert notif["Title"] == "Asset Pending Approval"
    assert "asset-123" in notif["Message"]
    assert notif["ReferenceID"] == "asset-123"
    assert notif["ReferenceType"] == "ASSET"
    assert notif["IsRead"] is False
    assert "CreatedAt" in notif
    assert "ExpiresAt" in notif
    assert "TTL" in notif
    assert notif["EntityType"] == "NOTIFICATION"

    sk_parts = notif["SK"].split("#")
    assert len(sk_parts) == 3
    notification_id = sk_parts[2]
    parsed_uuid = uuid.UUID(notification_id, version=4)
    assert str(parsed_uuid) == notification_id


# ---------------------------------------------------------------------------
# Property 6: Fan-out count
# ---------------------------------------------------------------------------


def test_fanout_creates_one_notification_per_recipient(mock_dynamodb):
    """Property 6: 3 active management users → exactly 3 notification records."""
    table = mock_dynamodb
    mod = _import_processor()

    user_ids = _seed_users(table, "management", 3)

    rule = {
        "notification_type": "ASSET_PENDING_APPROVAL",
        "target_role": "management",
        "recipient_field": None,
        "title": "Asset Pending Approval",
        "message_template": "Asset {reference_id} requires your approval.",
        "reference_type": "ASSET",
    }

    recipients = mod["resolve_recipients"](rule, {})
    assert len(recipients) == 3

    mod["create_notifications"](recipients, rule, "asset-xyz")

    from boto3.dynamodb.conditions import Key

    for uid in user_ids:
        response = table.query(KeyConditionExpression=Key("PK").eq(f"USER#{uid}"))
        notifications = [
            i for i in response["Items"] if i["SK"].startswith("NOTIFICATION#")
        ]
        assert len(notifications) == 1


# ---------------------------------------------------------------------------
# Property 12: TTL calculation
# ---------------------------------------------------------------------------


def test_ttl_calculation(mock_dynamodb):
    """Property 12: ExpiresAt = CreatedAt epoch + 7,776,000 seconds and TTL = ExpiresAt."""
    table = mock_dynamodb
    mod = _import_processor()

    rule = {
        "notification_type": "ASSET_PENDING_APPROVAL",
        "title": "Test",
        "message_template": "Test {reference_id}",
        "reference_type": "ASSET",
    }
    mod["create_notifications"](["user-ttl"], rule, "ref-1")

    from boto3.dynamodb.conditions import Key

    response = table.query(KeyConditionExpression=Key("PK").eq("USER#user-ttl"))
    notifications = [
        i for i in response["Items"] if i["SK"].startswith("NOTIFICATION#")
    ]
    assert len(notifications) == 1
    notif = notifications[0]

    created_at = datetime.fromisoformat(notif["CreatedAt"])
    created_epoch = int(created_at.timestamp())
    expected_expires = created_epoch + 7_776_000

    assert int(notif["ExpiresAt"]) == expected_expires
    assert int(notif["TTL"]) == int(notif["ExpiresAt"])


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


def test_deserialize_image(mock_dynamodb):
    """Verify _deserialize_image converts DynamoDB JSON to plain dict."""
    mod = _import_processor()

    image = {
        "PK": {"S": "ASSET#a1"},
        "SK": {"S": "METADATA"},
        "Status": {"S": "IN_STOCK"},
        "IsActive": {"BOOL": True},
    }
    result = mod["_deserialize_image"](image)
    assert result == {
        "PK": "ASSET#a1",
        "SK": "METADATA",
        "Status": "IN_STOCK",
        "IsActive": True,
    }


def test_get_entity_prefix_metadata(mock_dynamodb):
    mod = _import_processor()
    assert mod["_get_entity_prefix"]("METADATA") == "METADATA"


def test_get_entity_prefix_issue(mock_dynamodb):
    mod = _import_processor()
    assert mod["_get_entity_prefix"]("ISSUE#2024-01-01T00:00:00+00:00") == "ISSUE#"


def test_get_entity_prefix_handover(mock_dynamodb):
    mod = _import_processor()
    assert (
        mod["_get_entity_prefix"]("HANDOVER#2024-07-01T10:00:00+00:00") == "HANDOVER#"
    )


def test_extract_reference_id_metadata(mock_dynamodb):
    mod = _import_processor()
    new_image = {"PK": "ASSET#laptop-001", "SK": "METADATA"}
    assert mod["_extract_reference_id"](new_image, "METADATA") == "laptop-001"


def test_extract_reference_id_issue(mock_dynamodb):
    mod = _import_processor()
    new_image = {"PK": "ASSET#a1", "SK": "ISSUE#2024-08-01T12:00:00+00:00"}
    assert (
        mod["_extract_reference_id"](new_image, "ISSUE#") == "2024-08-01T12:00:00+00:00"
    )
