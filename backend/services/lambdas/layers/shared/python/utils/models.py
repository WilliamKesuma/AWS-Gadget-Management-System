from __future__ import annotations

from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field
from utils.enums import (
    Asset_Status_Enum,
    Asset_Condition_Enum,
    Issue_Status_Enum,
    Issue_Category_Enum,
    Software_Status_Enum,
    Scan_Status_Enum,
    User_Status_Enum,
    Return_Condition_Enum,
    Return_Status_Enum,
    Reset_Status_Enum,
    Return_Trigger_Enum,
    Finance_Notification_Status_Enum,
    Data_Access_Impact_Enum,
    Risk_Level_Enum,
    Notification_Type_Enum,
    Reference_Type_Enum,
    Maintenance_Record_Type_Enum,
    Activity_Type_Enum,
    Target_Type_Enum,
    Approval_Type_Enum,
)


# ---------------------------------------------------------------------------
# Upload Session
# PK: SESSION#<UploadSessionID>  |  SK: METADATA
# ---------------------------------------------------------------------------
class UploadSessionModel(BaseModel):
    PK: str = Field(..., description="SESSION#<UploadSessionID>")
    SK: str = Field(default="METADATA")

    UploadSessionID: str
    InvoiceS3Key: str
    GadgetPhotoS3Keys: list[str]
    CreatedAt: str
    TTL: int  # Unix epoch — DynamoDB auto-cleanup after 1 hour


# ---------------------------------------------------------------------------
# Scan Job
# PK: SCAN#<ScanJobID>  |  SK: METADATA
# ---------------------------------------------------------------------------
class ExtractedFieldValue(BaseModel):
    value: Optional[str] = None
    confidence: Optional[Decimal] = None
    alternative_value: Optional[str] = None
    alternative_confidence: Optional[Decimal] = None


class ScanJobModel(BaseModel):
    PK: str = Field(..., description="SCAN#<ScanJobID>")
    SK: str = Field(default="METADATA")

    ScanJobID: str
    UploadSessionID: str
    Status: Scan_Status_Enum  # PROCESSING | COMPLETED | SCAN_FAILED
    FailureReason: Optional[str] = None
    TextractJobId: Optional[str] = None
    CreatedAt: str

    # Extracted fields with confidence scores (populated on COMPLETED)
    InvoiceNumber: Optional[ExtractedFieldValue] = None
    Vendor: Optional[ExtractedFieldValue] = None
    PurchaseDate: Optional[ExtractedFieldValue] = None
    SerialNumber: Optional[ExtractedFieldValue] = None
    Brand: Optional[ExtractedFieldValue] = None
    Model: Optional[ExtractedFieldValue] = None
    ProductDescription: Optional[ExtractedFieldValue] = None
    Cost: Optional[ExtractedFieldValue] = None
    PaymentMethod: Optional[ExtractedFieldValue] = None
    Processor: Optional[ExtractedFieldValue] = None
    Storage: Optional[ExtractedFieldValue] = None
    OSVersion: Optional[ExtractedFieldValue] = None
    Memory: Optional[ExtractedFieldValue] = None


# ---------------------------------------------------------------------------
# Asset Metadata (Core Record)
# PK: ASSET#<AssetID>  |  SK: METADATA
# ---------------------------------------------------------------------------
class AssetMetadataModel(BaseModel):
    PK: str = Field(..., description="ASSET#<AssetID>")
    SK: str = Field(default="METADATA")

    # AI OCR extracted fields (confirmed by IT Admin)
    InvoiceNumber: Optional[str] = None
    Vendor: Optional[str] = None
    PurchaseDate: Optional[str] = None
    SerialNumber: Optional[str] = None
    Brand: Optional[str] = None
    Model: Optional[str] = None
    ProductDescription: Optional[str] = None
    Cost: Optional[Decimal] = None
    PaymentMethod: Optional[str] = None

    # S3 evidence paths
    InvoiceS3Key: Optional[str] = None
    GadgetPhotoS3Keys: Optional[list[str]] = None

    # Textract-extracted hardware specs (confirmed by IT Admin)
    Processor: Optional[str] = None
    Storage: Optional[str] = None
    OSVersion: Optional[str] = None
    Memory: Optional[str] = None

    # Lifecycle state
    Status: Asset_Status_Enum
    Category: Optional[str] = None
    Condition: Optional[Asset_Condition_Enum] = None
    Remarks: Optional[str] = None
    RejectionReason: Optional[str] = None
    CreatedAt: Optional[str] = None

    # Record lock (set by CompleteDisposal)
    IsLocked: bool = Field(default=False)

    # EntityTypeIndex — fixed value enables "list all assets" query
    EntityType: str = Field(
        default="ASSET", description="Fixed value for EntityTypeIndex GSI"
    )

    # StatusIndex (GSI2) projection
    StatusIndexPK: Optional[str] = Field(default=None, description="STATUS#<Status>")
    StatusIndexSK: Optional[str] = Field(default=None, description="ASSET#<AssetID>")

    # SerialNumberIndex (GSI3) projection
    SerialNumberIndexPK: Optional[str] = Field(
        default=None, description="SERIAL#<SerialNumber>"
    )
    SerialNumberIndexSK: Optional[str] = Field(default="METADATA")

    # EmployeeAssetIndex (GSI4) projection
    EmployeeAssetIndexPK: Optional[str] = Field(
        default=None, description="EMPLOYEE#<EmployeeID>"
    )
    EmployeeAssetIndexSK: Optional[str] = Field(
        default=None, description="ASSET#<AssignmentDate>"
    )


# ---------------------------------------------------------------------------
# Handover Record
# PK: ASSET#<AssetID>  |  SK: HANDOVER#<HandoverID>
# ---------------------------------------------------------------------------
class HandoverRecordModel(BaseModel):
    PK: str = Field(..., description="ASSET#<AssetID>")
    SK: str = Field(..., description="HANDOVER#<HandoverID>")

    HandoverID: str  # UUID v4 — used as the API path parameter

    EmployeeID: str
    EmployeeName: str
    EmployeeEmail: str
    AssignedByID: str
    AssignmentDate: str  # ISO-8601 UTC
    Notes: Optional[str] = None

    # S3 paths (populated progressively)
    HandoverFormS3Key: Optional[str] = None  # handovers/{asset_id}/{timestamp}.pdf
    HandoverFormHtmlS3Key: Optional[str] = None  # handovers/{asset_id}/{timestamp}.html
    SignedFormS3Key: Optional[str] = None  # handovers/{asset_id}/{timestamp}-signed.pdf
    SignatureS3Key: Optional[str] = (
        None  # signatures/{employee_id}/{asset_id}/{timestamp}.png
    )

    AcceptedAt: Optional[str] = None  # ISO-8601 UTC, set on acceptance

    # EmployeeAssetIndex GSI keys (denormalized for query)
    EmployeeAssetIndexPK: Optional[str] = Field(
        default=None, description="EMPLOYEE#<EmployeeID>"
    )
    EmployeeAssetIndexSK: Optional[str] = Field(
        default=None, description="ASSET#<AssignmentDate>"
    )


# ---------------------------------------------------------------------------
# Immutable Audit Trail
# PK: ASSET#<AssetID>  |  SK: LOG#<Timestamp>#<ActorID>
# ---------------------------------------------------------------------------
class AuditLogModel(BaseModel):
    PK: str = Field(..., description="ASSET#<AssetID>")
    SK: str = Field(..., description="LOG#<Timestamp>#<ActorID>")

    ActorID: str
    Phase: str
    PreviousStatus: str
    NewStatus: str
    RejectionReason: Optional[str] = None
    Remarks: Optional[str] = None
    AdminDigitalSignature: Optional[str] = None
    UserDigitalSignature: Optional[str] = None
    PhotoEvidenceURLs: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# Software Installation Governance
# PK: ASSET#<AssetID>  |  SK: SOFTWARE#<SoftwareRequestID>
# ---------------------------------------------------------------------------
class SoftwareInstallationModel(BaseModel):
    PK: str = Field(..., description="ASSET#<AssetID>")
    SK: str = Field(..., description="SOFTWARE#<SoftwareRequestID>")

    SoftwareRequestID: str  # Domain-prefixed ID (e.g. SOFTWARE-202605-1) — used as the API path parameter

    # Request fields
    SoftwareName: str
    Version: str
    Vendor: str
    Justification: str
    LicenseType: str
    LicenseValidityPeriod: str
    DataAccessImpact: Data_Access_Impact_Enum

    # Workflow state
    Status: Software_Status_Enum  # PENDING_REVIEW | ESCALATED_TO_MANAGEMENT | SOFTWARE_INSTALL_APPROVED | SOFTWARE_INSTALL_REJECTED
    RiskLevel: Optional[Risk_Level_Enum] = (
        None  # LOW | MEDIUM | HIGH (set during IT Admin review)
    )

    # Submission metadata
    RequestedBy: str  # Employee user ID (sub claim)
    CreatedAt: str  # ISO-8601 UTC

    # IT Admin review fields
    ReviewedBy: Optional[str] = None
    ReviewedAt: Optional[str] = None
    RejectionReason: Optional[str] = None

    # Management review fields
    ManagementReviewedBy: Optional[str] = None
    ManagementReviewedAt: Optional[str] = None
    ManagementRejectionReason: Optional[str] = None
    ManagementRemarks: Optional[str] = None

    # Installation
    InstallationTimestamp: Optional[str] = None

    # SoftwareStatusIndex GSI keys
    SoftwareStatusIndexPK: Optional[str] = Field(
        default=None, description="SOFTWARE_STATUS#<Status>"
    )
    SoftwareStatusIndexSK: Optional[str] = Field(
        default=None, description="SOFTWARE#<CreatedAt>"
    )

    # SoftwareEntityIndex GSI partition key (sort key is CreatedAt)
    SoftwareEntityType: str = Field(
        default="SOFTWARE_REQUEST",
        description="Fixed value for SoftwareEntityIndex GSI partition key",
    )

    # MaintenanceEntityIndex GSI keys
    MaintenanceEntityType: str = Field(
        default="MAINTENANCE",
        description="Fixed value for MaintenanceEntityIndex GSI partition key",
    )
    MaintenanceTimestamp: Optional[str] = Field(
        default=None,
        description="Normalized timestamp for MaintenanceEntityIndex sort key (same as CreatedAt)",
    )
    MaintenanceRecordType: Optional[Maintenance_Record_Type_Enum] = Field(
        default=Maintenance_Record_Type_Enum.SOFTWARE_REQUEST,
        description="Record type discriminator for maintenance history",
    )


# ---------------------------------------------------------------------------
# Issue & Repair Tickets
# PK: ASSET#<AssetID>  |  SK: ISSUE#<IssueID>
# ---------------------------------------------------------------------------
class IssueRepairModel(BaseModel):
    PK: str = Field(..., description="ASSET#<AssetID>")
    SK: str = Field(..., description="ISSUE#<IssueID>")

    IssueID: (
        str  # Domain-prefixed ID (e.g. ISSUE-202605-1) — used as the path parameter
    )

    # Core fields
    IssueDescription: str
    Category: Issue_Category_Enum  # SOFTWARE | HARDWARE
    Status: Issue_Status_Enum  # TROUBLESHOOTING | UNDER_REPAIR | SEND_WARRANTY | RESOLVED | REPLACEMENT_REQUIRED | REPLACEMENT_APPROVED | REPLACEMENT_REJECTED
    # Submission metadata
    ReportedBy: str  # Employee user ID
    CreatedAt: str  # ISO-8601 UTC

    # Resolution fields (set by IT_Admin)
    ResolvedBy: Optional[str] = None
    ResolvedAt: Optional[str] = None
    RepairNotes: Optional[str] = None

    # Warranty fields
    WarrantyNotes: Optional[str] = None
    WarrantySentAt: Optional[str] = None

    # Replacement fields
    ReplacementJustification: Optional[str] = None

    # Management review fields
    ManagementReviewedBy: Optional[str] = None
    ManagementReviewedAt: Optional[str] = None
    ManagementRejectionReason: Optional[str] = None
    ManagementRemarks: Optional[str] = None

    # Resolution path: "REPAIR" or "REPLACEMENT"
    ActionPath: Optional[str] = None

    # S3 evidence paths (populated by GenerateIssueUploadUrls)
    IssuePhotoS3Keys: Optional[list[str]] = None

    # Completion fields
    CompletedAt: Optional[str] = None
    CompletionNotes: Optional[str] = None

    # IssueStatusIndex GSI keys
    IssueStatusIndexPK: Optional[str] = Field(
        default=None, description="ISSUE_STATUS#<Status>"
    )
    IssueStatusIndexSK: Optional[str] = Field(
        default=None, description="ISSUE#<CreatedAt>"
    )

    # IssueEntityIndex GSI partition key (sort key is CreatedAt)
    IssueEntityType: str = Field(
        default="ISSUE",
        description="Fixed value for IssueEntityIndex GSI partition key",
    )

    # MaintenanceEntityIndex GSI keys
    MaintenanceEntityType: str = Field(
        default="MAINTENANCE",
        description="Fixed value for MaintenanceEntityIndex GSI partition key",
    )
    MaintenanceTimestamp: Optional[str] = Field(
        default=None,
        description="Normalized timestamp for MaintenanceEntityIndex sort key (same as CreatedAt)",
    )
    MaintenanceRecordType: Optional[Maintenance_Record_Type_Enum] = Field(
        default=Maintenance_Record_Type_Enum.ISSUE,
        description="Record type discriminator for maintenance history",
    )


# ---------------------------------------------------------------------------
# Asset Specs (snapshot captured at disposal initiation)
# ---------------------------------------------------------------------------
class AssetSpecsModel(BaseModel):
    """Asset specification snapshot captured at disposal initiation."""

    Brand: Optional[str] = None
    Model: Optional[str] = None
    SerialNumber: Optional[str] = None
    ProductDescription: Optional[str] = None
    Cost: Optional[Decimal] = None
    PurchaseDate: Optional[str] = None


# ---------------------------------------------------------------------------
# Disposal Record
# PK: ASSET#<AssetID>  |  SK: DISPOSAL#<DisposalID>
# ---------------------------------------------------------------------------
class DisposalRecordModel(BaseModel):
    PK: str = Field(..., description="ASSET#<AssetID>")
    SK: str = Field(..., description="DISPOSAL#<DisposalID>")

    DisposalID: str  # Domain-prefixed ID (e.g. DISPOSAL-202605-1)

    # Initiation fields
    DisposalReason: str
    Justification: str
    AssetSpecs: Optional[AssetSpecsModel] = None
    InitiatedBy: str
    InitiatedAt: str  # ISO-8601 UTC

    # Management review fields
    ManagementReviewedBy: Optional[str] = None
    ManagementReviewedAt: Optional[str] = None
    ManagementApprovedAt: Optional[str] = None
    ManagementRejectionReason: Optional[str] = None
    ManagementRemarks: Optional[str] = None

    # Completion fields
    DisposalDate: Optional[str] = None
    DataWipeConfirmed: Optional[bool] = None
    CompletedBy: Optional[str] = None
    CompletedAt: Optional[str] = None

    # Record lock
    IsLocked: bool = Field(default=False)

    # Finance notification
    FinanceNotifiedAt: Optional[str] = None
    FinanceNotificationSent: bool = Field(default=False)
    FinanceNotificationStatus: Optional[Finance_Notification_Status_Enum] = Field(
        default=None, description="QUEUED | COMPLETED | NO_FINANCE_USERS | FAILED"
    )

    # DisposalStatusIndex GSI keys
    DisposalStatusIndexPK: Optional[str] = Field(
        default=None, description="DISPOSAL_STATUS#<Status>"
    )
    DisposalStatusIndexSK: Optional[str] = Field(
        default=None, description="DISPOSAL#<DisposalID>"
    )

    # DisposalEntityIndex GSI partition key (sort key is InitiatedAt)
    DisposalEntityType: str = Field(
        default="DISPOSAL",
        description="Fixed value for DisposalEntityIndex GSI partition key",
    )

    # MaintenanceEntityIndex GSI keys
    MaintenanceEntityType: str = Field(
        default="MAINTENANCE",
        description="Fixed value for MaintenanceEntityIndex GSI partition key",
    )
    MaintenanceTimestamp: Optional[str] = Field(
        default=None,
        description="Normalized timestamp for MaintenanceEntityIndex sort key (same as InitiatedAt)",
    )
    MaintenanceRecordType: Optional[Maintenance_Record_Type_Enum] = Field(
        default=Maintenance_Record_Type_Enum.DISPOSAL,
        description="Record type discriminator for maintenance history",
    )


# ---------------------------------------------------------------------------
# GSI Key Helpers
# ---------------------------------------------------------------------------
class EmployeeAssetIndexKeys(BaseModel):
    """EmployeeAssetIndex (GSI1): Employee → Asset assignment lookup, sorted by handover date."""

    EmployeeAssetIndexPK: str = Field(..., description="EMPLOYEE#<EmployeeID>")
    EmployeeAssetIndexSK: str = Field(..., description="ASSET#<AssignmentDate>")


# ---------------------------------------------------------------------------
# User Metadata
# PK: USER#<UserID>  |  SK: METADATA
# ---------------------------------------------------------------------------
class UserMetadataModel(BaseModel):
    PK: str = Field(..., description="USER#<UserID>")
    SK: str = Field(default="METADATA")

    UserID: str
    Fullname: str
    Email: str
    Role: str  # it-admin | management | employee | finance
    Status: User_Status_Enum = Field(
        default=User_Status_Enum.ACTIVE
    )  # active | inactive
    CreatedAt: str
    EntityType: str = Field(
        default="USER", description="Fixed value for EntityTypeIndex GSI"
    )

    # Employee dashboard counters (maintained by CounterProcessor stream)
    AssignedAssets: int = Field(
        default=0, description="Count of assets currently assigned to this employee"
    )
    PendingRequests: int = Field(
        default=0, description="Count of non-terminal issues + software requests"
    )
    PendingSignatures: int = Field(
        default=0, description="Count of handovers/returns awaiting employee signature"
    )
    UnreadNotificationCount: int = Field(
        default=0, description="Count of unread notifications"
    )


# ---------------------------------------------------------------------------
# Return Record
# PK: ASSET#<AssetID>  |  SK: RETURN#<ReturnID>
# ---------------------------------------------------------------------------
class ReturnRecordModel(BaseModel):
    PK: str = Field(..., description="ASSET#<AssetID>")
    SK: str = Field(..., description="RETURN#<ReturnID>")

    ReturnID: str  # Domain-prefixed ID (e.g. RETURN-202605-1) — used as the API path parameter

    # Initiation fields (all set at creation time by IT Admin)
    ReturnTrigger: Return_Trigger_Enum
    InitiatedBy: str  # IT Admin actor_id (sub claim)
    InitiatedAt: str  # ISO-8601 UTC
    ConditionAssessment: Return_Condition_Enum  # GOOD | MINOR_DAMAGE | MINOR_DAMAGE_REPAIR_REQUIRED | MAJOR_DAMAGE
    Remarks: str
    ResetStatus: Reset_Status_Enum  # COMPLETE | INCOMPLETE

    # Asset snapshot (fetched from asset record at initiation)
    SerialNumber: Optional[str] = None
    Model: Optional[str] = None

    # Evidence S3 keys (populated by GenerateReturnUploadUrls — admin side)
    ReturnPhotoS3Keys: Optional[list[str]] = None
    AdminSignatureS3Key: Optional[str] = None

    # Completion fields (populated by CompleteReturn — employee side)
    UserSignatureS3Key: Optional[str] = None
    CompletedAt: Optional[str] = None  # ISO-8601 UTC
    CompletedBy: Optional[str] = None  # Employee actor_id

    # Return record lifecycle status (set on completion)
    ResolvedStatus: Optional[Return_Status_Enum] = None

    # MaintenanceEntityIndex GSI keys
    MaintenanceEntityType: str = Field(
        default="MAINTENANCE",
        description="Fixed value for MaintenanceEntityIndex GSI partition key",
    )
    MaintenanceTimestamp: Optional[str] = Field(
        default=None,
        description="Normalized timestamp for MaintenanceEntityIndex sort key (same as InitiatedAt)",
    )
    MaintenanceRecordType: Optional[Maintenance_Record_Type_Enum] = Field(
        default=Maintenance_Record_Type_Enum.RETURN,
        description="Record type discriminator for maintenance history",
    )


# ---------------------------------------------------------------------------
# Finance Notification Record
# PK: ASSET#<AssetID>  |  SK: FINANCE_NOTIFICATION#<NotifiedAt>#<RecipientUserID>
# ---------------------------------------------------------------------------
class FinanceNotificationRecordModel(BaseModel):
    PK: str = Field(..., description="ASSET#<AssetID>")
    SK: str = Field(
        ...,
        description="FINANCE_NOTIFICATION#<NotifiedAt>#<RecipientUserID>",
    )

    RecipientUserID: str
    NotifiedAt: str  # ISO-8601 UTC

    # Financial payload
    AssetID: str
    SerialNumber: Optional[str] = None
    PurchaseDate: Optional[str] = None
    OriginalCost: Optional[Decimal] = None
    DisposalDate: str
    DisposalReason: str


# ---------------------------------------------------------------------------
# Asset Category Record
# PK: CATEGORY#<CategoryID>  |  SK: METADATA
# ---------------------------------------------------------------------------
class AssetCategoryModel(BaseModel):
    PK: str = Field(..., description="CATEGORY#<CategoryID>")
    SK: str = Field(default="METADATA")

    CategoryID: str  # UUID v4
    CategoryName: str  # SCREAMING_SNAKE_CASE
    CreatedAt: str  # ISO-8601 UTC

    # CategoryEntityIndex GSI — enables listing all categories
    CategoryEntityType: str = Field(
        default="CATEGORY",
        description="Fixed value for CategoryEntityIndex GSI partition key",
    )

    # CategoryNameIndex GSI — enables O(1) uniqueness check by name
    CategoryNameIndexPK: Optional[str] = Field(
        default=None, description="CATEGORY_NAME#<CategoryName>"
    )


# ---------------------------------------------------------------------------
# Category Counter (atomic asset ID generation)
# PK: COUNTER#<Category>#<Year>  |  SK: METADATA
# ---------------------------------------------------------------------------
class CategoryCounterModel(BaseModel):
    PK: str = Field(..., description="COUNTER#<Category>#<Year>")
    SK: str = Field(default="METADATA")
    Count: int


# ---------------------------------------------------------------------------
# Domain Counter (atomic domain-prefixed ID generation)
# PK: DOMAIN_COUNTER#<Domain>#<YYYYMM>  |  SK: METADATA
# ---------------------------------------------------------------------------
class DomainCounterModel(BaseModel):
    PK: str = Field(..., description="DOMAIN_COUNTER#<Domain>#<YYYYMM>")
    SK: str = Field(default="METADATA")
    Count: int


# ---------------------------------------------------------------------------
# Entity Counter (Dashboard)
# PK: ENTITY_COUNTERS  |  SK: METADATA
# ---------------------------------------------------------------------------
class EntityCounterModel(BaseModel):
    PK: str = Field(default="ENTITY_COUNTERS")
    SK: str = Field(default="METADATA")

    AssetCount: int = Field(default=0)
    IssueCount: int = Field(default=0)
    ReturnCount: int = Field(default=0)
    DisposalCount: int = Field(default=0)
    AssignmentCount: int = Field(default=0)
    SoftwareRequestCount: int = Field(default=0)


# ---------------------------------------------------------------------------
# Notification Record
# PK: USER#<RecipientUserID>  |  SK: NOTIFICATION#<Timestamp>#<NotificationID>
# ---------------------------------------------------------------------------
class NotificationRecordModel(BaseModel):
    PK: str = Field(..., description="USER#<RecipientUserID>")
    SK: str = Field(..., description="NOTIFICATION#<Timestamp>#<NotificationID>")

    NotificationType: Notification_Type_Enum
    Title: str
    Message: str
    ReferenceID: str
    ReferenceType: Reference_Type_Enum
    IsRead: bool = Field(default=False)
    CreatedAt: str
    ExpiresAt: int  # Unix epoch
    TTL: int  # Same as ExpiresAt, mapped to DynamoDB TTL attribute
    EntityType: str = Field(default="NOTIFICATION")


# ---------------------------------------------------------------------------
# Dashboard Counter (pre-computed by CounterProcessor stream)
# PK: DASHBOARD_COUNTERS  |  SK: METADATA
# ---------------------------------------------------------------------------
class DashboardCounterModel(BaseModel):
    PK: str = Field(default="DASHBOARD_COUNTERS")
    SK: str = Field(default="METADATA")

    # IT Admin / Management shared
    TotalActiveAssets: int = Field(default=0)
    InMaintenance: int = Field(default=0)

    # IT Admin specific
    PendingIssues: int = Field(default=0)

    # Management specific
    PendingApprovals: int = Field(default=0)
    ScheduledDisposals: int = Field(default=0)

    # Finance specific
    TotalDisposed: int = Field(default=0)
    TotalAssetValue: int = Field(default=0)

    # Assets page stats
    InStock: int = Field(default=0)
    Assigned: int = Field(default=0)

    # Requests page stats
    TotalActiveRequests: int = Field(default=0)
    PendingReturns: int = Field(default=0)

    # Asset distribution (category → count)
    CategoryCounts: Optional[dict] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Activity Record (written by Lambdas for dashboard recent activity)
# PK: ACTIVITY#<ActivityID>  |  SK: METADATA
# ---------------------------------------------------------------------------
class ActivityRecordModel(BaseModel):
    PK: str = Field(..., description="ACTIVITY#<ActivityID>")
    SK: str = Field(default="METADATA")

    ActivityID: str
    Activity: str  # Human-readable description
    ActivityType: Activity_Type_Enum
    ActorID: str
    ActorName: str
    ActorRole: str
    TargetID: str
    TargetType: Target_Type_Enum
    Timestamp: str  # ISO-8601 UTC

    # ActivityEntityIndex GSI keys
    ActivityEntityType: str = Field(
        default="ACTIVITY",
        description="Fixed value for ActivityEntityIndex GSI partition key",
    )
