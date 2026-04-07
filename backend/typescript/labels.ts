/**
 * Human-readable labels for all enum values.
 * Each label map is typed as Record<EnumType, string> so TypeScript
 * will error if a new value is added to the schema without a label.
 */

import type {
    AssetStatus,
    IssueStatus,
    SoftwareStatus,
    ScanStatus,
    UserStatus,
    UserRole,
    ReturnCondition,
    ResetStatus,
    ReturnTrigger,
    FinanceNotificationStatus,
    AssetCategory,
    IssueCategory,
    DataAccessImpact,
    RiskLevel,
    FileManifestItemType,
    ReturnFileManifestItemType,
    DocumentType,
    ApproveRejectDecision,
    ReviewDecision,
    SortOrder,
} from "./types"

export const AssetStatusLabels: Record<AssetStatus, string> = {
    IN_STOCK: "In Stock",
    ASSIGNED: "Assigned",
    ASSET_PENDING_APPROVAL: "Pending Approval",
    ASSET_REJECTED: "Rejected",
    DISPOSAL_REVIEW: "Disposal Review",
    DISPOSAL_PENDING: "Disposal Pending",
    DISPOSAL_REJECTED: "Disposal Rejected",
    DISPOSED: "Disposed",
    RETURN_PENDING: "Return Pending",
    DAMAGED: "Damaged",
    REPAIR_REQUIRED: "Repair Required",
    UNDER_REPAIR: "Under Repair",
    ISSUE_REPORTED: "Issue Reported",
}

export const IssueStatusLabels: Record<IssueStatus, string> = {
    TROUBLESHOOTING: "Troubleshooting",
    UNDER_REPAIR: "Under Repair",
    SEND_WARRANTY: "Sent to Warranty",
    RESOLVED: "Resolved",
    REPLACEMENT_REQUIRED: "Replacement Required",
    REPLACEMENT_APPROVED: "Replacement Approved",
    REPLACEMENT_REJECTED: "Replacement Rejected",
}

export const SoftwareStatusLabels: Record<SoftwareStatus, string> = {
    PENDING_REVIEW: "Pending Review",
    ESCALATED_TO_MANAGEMENT: "Escalated to Management",
    SOFTWARE_INSTALL_APPROVED: "Approved",
    SOFTWARE_INSTALL_REJECTED: "Rejected",
}

export const ScanStatusLabels: Record<ScanStatus, string> = {
    PROCESSING: "Processing",
    COMPLETED: "Completed",
    SCAN_FAILED: "Scan Failed",
}

export const UserStatusLabels: Record<UserStatus, string> = {
    active: "Active",
    inactive: "Inactive",
}

export const UserRoleLabels: Record<UserRole, string> = {
    "it-admin": "IT Admin",
    management: "Management",
    employee: "Employee",
    finance: "Finance",
}

export const ReturnConditionLabels: Record<ReturnCondition, string> = {
    GOOD: "Good",
    MINOR_DAMAGE: "Minor Damage",
    MINOR_DAMAGE_REPAIR_REQUIRED: "Minor Damage (Repair Required)",
    MAJOR_DAMAGE: "Major Damage",
}

export const ResetStatusLabels: Record<ResetStatus, string> = {
    COMPLETE: "Complete",
    INCOMPLETE: "Incomplete",
}

export const ReturnTriggerLabels: Record<ReturnTrigger, string> = {
    RESIGNATION: "Resignation",
    REPLACEMENT: "Replacement",
    TRANSFER: "Transfer",
    IT_RECALL: "IT Recall",
    UPGRADE: "Upgrade",
}

export const FinanceNotificationStatusLabels: Record<FinanceNotificationStatus, string> = {
    QUEUED: "Queued",
    COMPLETED: "Completed",
    NO_FINANCE_USERS: "No Finance Users",
    FAILED: "Failed",
}

export const AssetCategoryLabels: Record<AssetCategory, string> = {
    LAPTOP: "Laptop",
    MOBILE_PHONE: "Mobile Phone",
    TABLET: "Tablet",
    OTHERS: "Others",
}

export const IssueCategoryLabels: Record<IssueCategory, string> = {
    SOFTWARE: "Software",
    HARDWARE: "Hardware",
}

export const DataAccessImpactLabels: Record<DataAccessImpact, string> = {
    LOW: "Low",
    MEDIUM: "Medium",
    HIGH: "High",
}

export const RiskLevelLabels: Record<RiskLevel, string> = {
    LOW: "Low",
    MEDIUM: "Medium",
    HIGH: "High",
}

export const FileManifestItemTypeLabels: Record<FileManifestItemType, string> = {
    invoice: "Invoice",
    gadget_photo: "Gadget Photo",
}

export const ReturnFileManifestItemTypeLabels: Record<ReturnFileManifestItemType, string> = {
    photo: "Photo",
    "admin-signature": "Admin Signature",
    "user-signature": "User Signature",
}

export const DocumentTypeLabels: Record<DocumentType, string> = {
    handover: "Handover",
    return: "Return",
}

export const ApproveRejectDecisionLabels: Record<ApproveRejectDecision, string> = {
    APPROVE: "Approve",
    REJECT: "Reject",
}

export const ReviewDecisionLabels: Record<ReviewDecision, string> = {
    APPROVE: "Approve",
    ESCALATE: "Escalate",
    REJECT: "Reject",
}

export const SortOrderLabels: Record<SortOrder, string> = {
    asc: "Ascending",
    desc: "Descending",
}

