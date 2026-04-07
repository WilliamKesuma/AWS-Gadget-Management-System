"""Unit tests for utils/enums.py — verifies enum definitions and backward compatibility."""

import pytest
from utils.enums import (
    Asset_Status_Enum,
    Issue_Status_Enum,
    Software_Status_Enum,
    Scan_Status_Enum,
    User_Status_Enum,
    Return_Condition_Enum,
    Reset_Status_Enum,
    Return_Trigger_Enum,
    Finance_Notification_Status_Enum,
)


class TestEnumStrInheritance:
    """All enums must inherit from str for DynamoDB/JSON backward compatibility."""

    def test_asset_status_is_str(self):
        assert isinstance(Asset_Status_Enum.IN_STOCK, str)

    def test_issue_status_is_str(self):
        assert isinstance(Issue_Status_Enum.TROUBLESHOOTING, str)

    def test_software_status_is_str(self):
        assert isinstance(Software_Status_Enum.PENDING_REVIEW, str)

    def test_scan_status_is_str(self):
        assert isinstance(Scan_Status_Enum.PROCESSING, str)

    def test_user_status_is_str(self):
        assert isinstance(User_Status_Enum.ACTIVE, str)

    def test_return_condition_is_str(self):
        assert isinstance(Return_Condition_Enum.GOOD, str)

    def test_reset_status_is_str(self):
        assert isinstance(Reset_Status_Enum.COMPLETE, str)

    def test_return_trigger_is_str(self):
        assert isinstance(Return_Trigger_Enum.RESIGNATION, str)

    def test_finance_notification_status_is_str(self):
        assert isinstance(Finance_Notification_Status_Enum.QUEUED, str)


class TestEnumValues:
    """Enum values must exactly match the strings stored in DynamoDB."""

    def test_asset_status_values(self):
        assert Asset_Status_Enum.IN_STOCK == "IN_STOCK"
        assert Asset_Status_Enum.ASSIGNED == "ASSIGNED"
        assert Asset_Status_Enum.DISPOSAL_PENDING == "DISPOSAL_PENDING"
        assert Asset_Status_Enum.DISPOSED == "DISPOSED"
        assert Asset_Status_Enum.RETURN_PENDING == "RETURN_PENDING"

    def test_user_status_lowercase_values(self):
        # User status uses lowercase to match Cognito/DynamoDB convention
        assert User_Status_Enum.ACTIVE == "active"
        assert User_Status_Enum.INACTIVE == "inactive"

    def test_scan_status_values(self):
        assert Scan_Status_Enum.PROCESSING == "PROCESSING"
        assert Scan_Status_Enum.COMPLETED == "COMPLETED"
        assert Scan_Status_Enum.SCAN_FAILED == "SCAN_FAILED"

    def test_software_status_values(self):
        assert Software_Status_Enum.PENDING_REVIEW == "PENDING_REVIEW"
        assert Software_Status_Enum.ESCALATED_TO_MANAGEMENT == "ESCALATED_TO_MANAGEMENT"
        assert (
            Software_Status_Enum.SOFTWARE_INSTALL_APPROVED
            == "SOFTWARE_INSTALL_APPROVED"
        )
        assert (
            Software_Status_Enum.SOFTWARE_INSTALL_REJECTED
            == "SOFTWARE_INSTALL_REJECTED"
        )


class TestEnumStringEquality:
    """Enum members must compare equal to their plain string equivalents."""

    def test_asset_status_equals_string(self):
        assert Asset_Status_Enum.IN_STOCK == "IN_STOCK"
        assert "IN_STOCK" == Asset_Status_Enum.IN_STOCK

    def test_user_status_equals_string(self):
        assert User_Status_Enum.ACTIVE == "active"
        assert "active" == User_Status_Enum.ACTIVE

    def test_enum_in_fstring(self):
        # GSI key construction pattern used in Lambda handlers — must use .value in Python 3.12+
        key = f"STATUS#{Asset_Status_Enum.ASSIGNED.value}"
        assert key == "STATUS#ASSIGNED"

    def test_enum_usable_as_dict_value(self):
        # Simulates DynamoDB update_item usage
        update = {"Status": Asset_Status_Enum.IN_STOCK}
        assert update["Status"] == "IN_STOCK"


class TestEnumMembership:
    """Verify all expected members exist on each enum."""

    def test_asset_status_has_all_members(self):
        expected = {
            "IN_STOCK",
            "ASSIGNED",
            "ASSET_PENDING_APPROVAL",
            "ASSET_REJECTED",
            "DISPOSAL_REVIEW",
            "DISPOSAL_PENDING",
            "DISPOSAL_REJECTED",
            "DISPOSED",
            "RETURN_PENDING",
            "DAMAGED",
            "REPAIR_REQUIRED",
            "UNDER_REPAIR",
            "ISSUE_REPORTED",
        }
        assert {m.name for m in Asset_Status_Enum} == expected

    def test_issue_status_has_all_members(self):
        expected = {
            "TROUBLESHOOTING",
            "UNDER_REPAIR",
            "SEND_WARRANTY",
            "RESOLVED",
            "REPLACEMENT_REQUIRED",
            "REPLACEMENT_APPROVED",
            "REPLACEMENT_REJECTED",
        }
        assert {m.name for m in Issue_Status_Enum} == expected

    def test_return_trigger_has_all_members(self):
        expected = {"RESIGNATION", "REPLACEMENT", "TRANSFER", "IT_RECALL", "UPGRADE"}
        assert {m.name for m in Return_Trigger_Enum} == expected
