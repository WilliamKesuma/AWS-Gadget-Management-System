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
  ReturnStatus,
  ReturnTrigger,
  FinanceNotificationStatus,
  AssetCondition,
  IssueCategory,
  DataAccessImpact,
  RiskLevel,
  NotificationType,
  ReferenceType,
  MaintenanceRecordType,
  DisposalStatus,
} from './types'

export const AssetStatusLabels: Record<AssetStatus, string> = {
  IN_STOCK: 'In Stock',
  ASSIGNED: 'Assigned',
  ASSET_PENDING_APPROVAL: 'Pending Approval',
  ISSUE_REPORTED: 'Issue Reported',
  ASSET_REJECTED: 'Rejected',
  DISPOSAL_REVIEW: 'Disposal Review',
  DISPOSAL_PENDING: 'Disposal Pending',
  DISPOSAL_REJECTED: 'Disposal Rejected',
  DISPOSED: 'Disposed',
  RETURN_PENDING: 'Return Pending',
  DAMAGED: 'Damaged',
  UNDER_REPAIR: 'Under Repair',
  REPAIR_REQUIRED: 'Repair Required',
}

export const IssueStatusLabels: Record<IssueStatus, string> = {
  TROUBLESHOOTING: 'Troubleshooting',
  UNDER_REPAIR: 'Under Repair',
  SEND_WARRANTY: 'Sent to Warranty',
  RESOLVED: 'Resolved',
  REPLACEMENT_REQUIRED: 'Replacement Required',
  REPLACEMENT_APPROVED: 'Replacement Approved',
  REPLACEMENT_REJECTED: 'Replacement Rejected',
}

export const SoftwareStatusLabels: Record<SoftwareStatus, string> = {
  PENDING_REVIEW: 'Pending Review',
  ESCALATED_TO_MANAGEMENT: 'Escalated to Management',
  SOFTWARE_INSTALL_APPROVED: 'Approved',
  SOFTWARE_INSTALL_REJECTED: 'Rejected',
}

export const ScanStatusLabels: Record<ScanStatus, string> = {
  PROCESSING: 'Processing',
  COMPLETED: 'Completed',
  SCAN_FAILED: 'Scan Failed',
}

export const UserStatusLabels: Record<UserStatus, string> = {
  active: 'Active',
  inactive: 'Inactive',
}

export const UserRoleLabels: Record<UserRole, string> = {
  'it-admin': 'IT Admin',
  management: 'Management',
  employee: 'Employee',
  finance: 'Finance',
}

export const ReturnConditionLabels: Record<ReturnCondition, string> = {
  GOOD: 'Good',
  MINOR_DAMAGE: 'Minor Damage',
  MINOR_DAMAGE_REPAIR_REQUIRED: 'Minor Damage (Repair Required)',
  MAJOR_DAMAGE: 'Major Damage',
}

export const ResetStatusLabels: Record<ResetStatus, string> = {
  COMPLETE: 'Complete',
  INCOMPLETE: 'Incomplete',
}

export const ReturnStatusLabels: Record<ReturnStatus, string> = {
  RETURN_PENDING: 'Return Pending',
  COMPLETED: 'Completed',
}

export const ReturnTriggerLabels: Record<ReturnTrigger, string> = {
  RESIGNATION: 'Resignation',
  REPLACEMENT: 'Replacement',
  TRANSFER: 'Transfer',
  IT_RECALL: 'IT Recall',
  UPGRADE: 'Upgrade',
}

export const FinanceNotificationStatusLabels: Record<
  FinanceNotificationStatus,
  string
> = {
  QUEUED: 'Queued',
  COMPLETED: 'Completed',
  NO_FINANCE_USERS: 'No Finance Users',
  FAILED: 'Failed',
}

export const AssetConditionLabels: Record<AssetCondition, string> = {
  GOOD: 'Good',
  FAIR: 'Fair',
  POOR: 'Poor',
}

export const IssueCategoryLabels: Record<IssueCategory, string> = {
  SOFTWARE: 'Software',
  HARDWARE: 'Hardware',
}

export const DataAccessImpactLabels: Record<DataAccessImpact, string> = {
  LOW: 'Low',
  MEDIUM: 'Medium',
  HIGH: 'High',
}

export const RiskLevelLabels: Record<RiskLevel, string> = {
  LOW: 'Low',
  MEDIUM: 'Medium',
  HIGH: 'High',
}

export const NotificationTypeLabels: Record<NotificationType, string> = {
  ASSET_PENDING_APPROVAL: 'Asset Pending Approval',
  REPLACEMENT_APPROVAL_NEEDED: 'Replacement Approval Needed',
  SOFTWARE_INSTALL_ESCALATION: 'Software Install Escalation',
  DISPOSAL_APPROVAL_NEEDED: 'Disposal Approval Needed',
  ASSET_APPROVED: 'Asset Approved',
  ASSET_REJECTED: 'Asset Rejected',
  NEW_ISSUE_REPORTED: 'New Issue Reported',
  REPLACEMENT_APPROVED: 'Replacement Approved',
  REPLACEMENT_REJECTED: 'Replacement Rejected',
  NEW_SOFTWARE_INSTALL_REQUEST: 'New Software Install Request',
  HANDOVER_ACCEPTED: 'Handover Accepted',
  AUDIT_DISPUTE_RAISED: 'Audit Dispute Raised',
  AUDIT_NON_RESPONSE_ESCALATION: 'Audit Non-Response Escalation',
  NEW_ASSET_ASSIGNED: 'New Asset Assigned',
  HANDOVER_FORM_READY: 'Handover Form Ready',
  SOFTWARE_INSTALL_APPROVED: 'Software Install Approved',
  SOFTWARE_INSTALL_REJECTED: 'Software Install Rejected',
  ISSUE_UNDER_REPAIR: 'Issue Under Repair',
  ISSUE_SENT_TO_WARRANTY: 'Issue Sent to Warranty',
  ISSUE_RESOLVED: 'Issue Resolved',
  RETURN_INITIATED: 'Return Initiated',
  AUDIT_CONFIRMATION_REQUIRED: 'Audit Confirmation Required',
  AUDIT_FINAL_ACKNOWLEDGEMENT: 'Audit Final Acknowledgement',
  AUDIT_DISPUTE_REVIEWED: 'Audit Dispute Reviewed',
  AUDIT_REMINDER: 'Audit Reminder',
  ASSET_DISPOSED_WRITEOFF: 'Asset Disposed (Write-Off)',
  REPLACEMENT_APPROVED_INFO: 'Replacement Approved (Info)',
}

export const ReferenceTypeLabels: Record<ReferenceType, string> = {
  ASSET: 'Asset',
  ISSUE: 'Issue',
  SOFTWARE: 'Software',
  DISPOSAL: 'Disposal',
  AUDIT: 'Audit',
  RETURN: 'Return',
}

export const MaintenanceRecordTypeLabels: Record<
  MaintenanceRecordType,
  string
> = {
  ISSUE: 'Issue',
  SOFTWARE_REQUEST: 'Software Request',
  RETURN: 'Return',
  DISPOSAL: 'Disposal',
}

export const DisposalStatusLabels: Record<DisposalStatus, string> = {
  DISPOSAL_PENDING: 'Disposal Pending',
  DISPOSAL_REJECTED: 'Disposal Rejected',
  DISPOSED: 'Disposed',
}

import type { ActivityType, ActivityTargetType, ApprovalType } from './types'

export const ActivityTypeLabels: Record<ActivityType, string> = {
  ASSET_CREATION: 'Asset Creation',
  ASSIGNMENT: 'Assignment',
  RETURN: 'Return',
  ISSUE: 'Issue',
  SOFTWARE_REQUEST: 'Software Request',
  DISPOSAL: 'Disposal',
  USER_CREATION: 'User Creation',
  APPROVAL: 'Approval',
  HANDOVER: 'Handover',
}

export const ActivityTargetTypeLabels: Record<ActivityTargetType, string> = {
  ASSET: 'Asset',
  ISSUE: 'Issue',
  SOFTWARE: 'Software',
  DISPOSAL: 'Disposal',
  USER: 'User',
  RETURN: 'Return',
}

export const ApprovalTypeLabels: Record<ApprovalType, string> = {
  ASSET_CREATION: 'Creation',
  REPLACEMENT: 'Replacement',
  SOFTWARE_ESCALATION: 'Software',
  DISPOSAL: 'Disposal',
}
