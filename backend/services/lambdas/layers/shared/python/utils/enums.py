"""
Status enumeration classes for the Gadget Management System.

This module defines all enum classes used throughout the system for status values,
condition assessments, and state management. All enums inherit from both str and Enum
to maintain backward compatibility with existing DynamoDB records while providing
type safety and IDE autocomplete support.
"""

from enum import Enum


class Asset_Status_Enum(str, Enum):
    """Asset lifecycle status values."""

    IN_STOCK = "IN_STOCK"
    ASSIGNED = "ASSIGNED"
    ASSET_PENDING_APPROVAL = "ASSET_PENDING_APPROVAL"
    ASSET_REJECTED = "ASSET_REJECTED"
    DISPOSAL_REVIEW = "DISPOSAL_REVIEW"
    DISPOSAL_PENDING = "DISPOSAL_PENDING"
    DISPOSAL_REJECTED = "DISPOSAL_REJECTED"
    DISPOSED = "DISPOSED"
    RETURN_PENDING = "RETURN_PENDING"
    DAMAGED = "DAMAGED"
    REPAIR_REQUIRED = "REPAIR_REQUIRED"
    UNDER_REPAIR = "UNDER_REPAIR"
    ISSUE_REPORTED = "ISSUE_REPORTED"


class Issue_Status_Enum(str, Enum):
    """Issue and repair ticket status values."""

    TROUBLESHOOTING = "TROUBLESHOOTING"
    UNDER_REPAIR = "UNDER_REPAIR"
    SEND_WARRANTY = "SEND_WARRANTY"
    RESOLVED = "RESOLVED"
    REPLACEMENT_REQUIRED = "REPLACEMENT_REQUIRED"
    REPLACEMENT_APPROVED = "REPLACEMENT_APPROVED"
    REPLACEMENT_REJECTED = "REPLACEMENT_REJECTED"


class Software_Status_Enum(str, Enum):
    """Software installation request status values."""

    PENDING_REVIEW = "PENDING_REVIEW"
    ESCALATED_TO_MANAGEMENT = "ESCALATED_TO_MANAGEMENT"
    SOFTWARE_INSTALL_APPROVED = "SOFTWARE_INSTALL_APPROVED"
    SOFTWARE_INSTALL_REJECTED = "SOFTWARE_INSTALL_REJECTED"


class Scan_Status_Enum(str, Enum):
    """Scan job processing status values."""

    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    SCAN_FAILED = "SCAN_FAILED"


class User_Status_Enum(str, Enum):
    """User account status values."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class User_Role_Enum(str, Enum):
    """User role values."""

    IT_ADMIN = "it-admin"
    MANAGEMENT = "management"
    EMPLOYEE = "employee"
    FINANCE = "finance"


class Return_Status_Enum(str, Enum):
    """Return record lifecycle status values."""

    RETURN_PENDING = "RETURN_PENDING"
    COMPLETED = "COMPLETED"


class Return_Condition_Enum(str, Enum):
    """Asset condition assessment values during returns."""

    GOOD = "GOOD"
    MINOR_DAMAGE = "MINOR_DAMAGE"
    MINOR_DAMAGE_REPAIR_REQUIRED = "MINOR_DAMAGE_REPAIR_REQUIRED"
    MAJOR_DAMAGE = "MAJOR_DAMAGE"


class Reset_Status_Enum(str, Enum):
    """Factory reset completion status values."""

    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


class Return_Trigger_Enum(str, Enum):
    """Asset return initiation trigger values."""

    RESIGNATION = "RESIGNATION"
    REPLACEMENT = "REPLACEMENT"
    TRANSFER = "TRANSFER"
    IT_RECALL = "IT_RECALL"
    UPGRADE = "UPGRADE"


class Finance_Notification_Status_Enum(str, Enum):
    """Finance notification delivery status values."""

    QUEUED = "QUEUED"
    COMPLETED = "COMPLETED"
    NO_FINANCE_USERS = "NO_FINANCE_USERS"
    FAILED = "FAILED"


class Data_Access_Impact_Enum(str, Enum):
    """Employee self-assessed data access impact level."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Risk_Level_Enum(str, Enum):
    """IT Admin risk assessment level for software installation requests."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Issue_Category_Enum(str, Enum):
    """Issue category values."""

    SOFTWARE = "SOFTWARE"
    HARDWARE = "HARDWARE"


class Asset_Condition_Enum(str, Enum):
    """Asset condition values set at creation time."""

    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"


class Notification_Type_Enum(str, Enum):
    """Notification type values for all roles."""

    # Management notifications
    ASSET_PENDING_APPROVAL = "ASSET_PENDING_APPROVAL"
    REPLACEMENT_APPROVAL_NEEDED = "REPLACEMENT_APPROVAL_NEEDED"
    SOFTWARE_INSTALL_ESCALATION = "SOFTWARE_INSTALL_ESCALATION"
    DISPOSAL_APPROVAL_NEEDED = "DISPOSAL_APPROVAL_NEEDED"

    # IT Admin notifications
    ASSET_APPROVED = "ASSET_APPROVED"
    ASSET_REJECTED = "ASSET_REJECTED"
    NEW_ISSUE_REPORTED = "NEW_ISSUE_REPORTED"
    REPLACEMENT_APPROVED = "REPLACEMENT_APPROVED"
    REPLACEMENT_REJECTED = "REPLACEMENT_REJECTED"
    NEW_SOFTWARE_INSTALL_REQUEST = "NEW_SOFTWARE_INSTALL_REQUEST"
    HANDOVER_ACCEPTED = "HANDOVER_ACCEPTED"
    AUDIT_DISPUTE_RAISED = "AUDIT_DISPUTE_RAISED"
    AUDIT_NON_RESPONSE_ESCALATION = "AUDIT_NON_RESPONSE_ESCALATION"

    # Employee notifications (user-specific)
    NEW_ASSET_ASSIGNED = "NEW_ASSET_ASSIGNED"
    HANDOVER_FORM_READY = "HANDOVER_FORM_READY"
    SOFTWARE_INSTALL_APPROVED = "SOFTWARE_INSTALL_APPROVED"
    SOFTWARE_INSTALL_REJECTED = "SOFTWARE_INSTALL_REJECTED"
    ISSUE_UNDER_REPAIR = "ISSUE_UNDER_REPAIR"
    ISSUE_SENT_TO_WARRANTY = "ISSUE_SENT_TO_WARRANTY"
    ISSUE_RESOLVED = "ISSUE_RESOLVED"
    RETURN_INITIATED = "RETURN_INITIATED"
    AUDIT_CONFIRMATION_REQUIRED = "AUDIT_CONFIRMATION_REQUIRED"
    AUDIT_FINAL_ACKNOWLEDGEMENT = "AUDIT_FINAL_ACKNOWLEDGEMENT"
    AUDIT_DISPUTE_REVIEWED = "AUDIT_DISPUTE_REVIEWED"
    AUDIT_REMINDER = "AUDIT_REMINDER"

    # Finance notifications
    ASSET_DISPOSED_WRITEOFF = "ASSET_DISPOSED_WRITEOFF"
    REPLACEMENT_APPROVED_INFO = "REPLACEMENT_APPROVED_INFO"


class Reference_Type_Enum(str, Enum):
    """Reference type values for notification records."""

    ASSET = "ASSET"
    ISSUE = "ISSUE"
    SOFTWARE = "SOFTWARE"
    DISPOSAL = "DISPOSAL"
    AUDIT = "AUDIT"
    RETURN = "RETURN"


class Maintenance_Record_Type_Enum(str, Enum):
    """Maintenance history record type values."""

    ISSUE = "ISSUE"
    SOFTWARE_REQUEST = "SOFTWARE_REQUEST"
    RETURN = "RETURN"
    DISPOSAL = "DISPOSAL"


class Activity_Type_Enum(str, Enum):
    """Dashboard recent activity type values."""

    ASSET_CREATION = "ASSET_CREATION"
    ASSIGNMENT = "ASSIGNMENT"
    RETURN = "RETURN"
    ISSUE = "ISSUE"
    SOFTWARE_REQUEST = "SOFTWARE_REQUEST"
    DISPOSAL = "DISPOSAL"
    USER_CREATION = "USER_CREATION"
    APPROVAL = "APPROVAL"
    HANDOVER = "HANDOVER"


class Target_Type_Enum(str, Enum):
    """Dashboard activity target type values."""

    ASSET = "ASSET"
    ISSUE = "ISSUE"
    SOFTWARE = "SOFTWARE"
    DISPOSAL = "DISPOSAL"
    USER = "USER"
    RETURN = "RETURN"


class Approval_Type_Enum(str, Enum):
    """Management approval hub item type values."""

    ASSET_CREATION = "ASSET_CREATION"
    REPLACEMENT = "REPLACEMENT"
    SOFTWARE_ESCALATION = "SOFTWARE_ESCALATION"
    DISPOSAL = "DISPOSAL"


class Disposal_Email_Event_Type_Enum(str, Enum):
    """SQS event type values for disposal email notifications.

    DEPRECATED — kept for backward compatibility.
    Use Email_Event_Type_Enum for all new email notifications.
    """

    DISPOSAL_PENDING = "DISPOSAL_PENDING"
    DISPOSAL_MANAGEMENT_APPROVED = "DISPOSAL_MANAGEMENT_APPROVED"


class Email_Event_Type_Enum(str, Enum):
    """Unified SQS event type values for all email notifications."""

    # Issue management
    ISSUE_SUBMITTED = "ISSUE_SUBMITTED"
    REPLACEMENT_REQUESTED = "REPLACEMENT_REQUESTED"

    # Software governance
    SOFTWARE_REQUEST_SUBMITTED = "SOFTWARE_REQUEST_SUBMITTED"

    # Return process
    RETURN_EVIDENCE_SUBMITTED = "RETURN_EVIDENCE_SUBMITTED"

    # Disposal process
    DISPOSAL_PENDING = "DISPOSAL_PENDING"
    DISPOSAL_MANAGEMENT_APPROVED = "DISPOSAL_MANAGEMENT_APPROVED"
