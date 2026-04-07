/**
 * Centralized Badge variant mappings for all status/enum values.
 *
 * Each map is typed as Record<EnumType, BadgeVariant> so TypeScript
 * will error if a new value is added to the schema without a variant.
 *
 * Import from here instead of defining inline variant maps in components.
 */

import type {
  AssetStatus,
  IssueStatus,
  SoftwareStatus,
  ReturnCondition,
  ResetStatus,
  ReturnStatus,
  FinanceNotificationStatus,
  RiskLevel,
  DataAccessImpact,
  IssueCategory,
  NotificationType,
  MaintenanceRecordType,
  AssetCondition,
  UserStatus,
  ScanStatus,
} from './types'

// Badge variant type matching the Badge component's variant prop
export type BadgeVariant =
  | 'default'
  | 'secondary'
  | 'destructive'
  | 'outline'
  | 'ghost'
  | 'link'
  | 'info'
  | 'warning'
  | 'danger'
  | 'success'

// ── Asset Status ──────────────────────────────────────────────────────────────

export const AssetStatusVariants: Record<AssetStatus, BadgeVariant> = {
  IN_STOCK: 'info',
  ASSIGNED: 'success',
  ASSET_PENDING_APPROVAL: 'warning',
  ASSET_REJECTED: 'danger',
  DISPOSAL_REVIEW: 'warning',
  DISPOSAL_PENDING: 'warning',
  DISPOSAL_REJECTED: 'danger',
  DISPOSED: 'default',
  RETURN_PENDING: 'warning',
  DAMAGED: 'danger',
  UNDER_REPAIR: 'warning',
  ISSUE_REPORTED: 'danger',
  REPAIR_REQUIRED: 'warning',
}

// ── Issue Status ──────────────────────────────────────────────────────────────

export const IssueStatusVariants: Record<IssueStatus, BadgeVariant> = {
  TROUBLESHOOTING: 'warning',
  UNDER_REPAIR: 'info',
  SEND_WARRANTY: 'info',
  RESOLVED: 'success',
  REPLACEMENT_REQUIRED: 'warning',
  REPLACEMENT_APPROVED: 'success',
  REPLACEMENT_REJECTED: 'danger',
}

// ── Software Status ───────────────────────────────────────────────────────────

export const SoftwareStatusVariants: Record<SoftwareStatus, BadgeVariant> = {
  PENDING_REVIEW: 'info',
  ESCALATED_TO_MANAGEMENT: 'warning',
  SOFTWARE_INSTALL_APPROVED: 'success',
  SOFTWARE_INSTALL_REJECTED: 'danger',
}

// ── Return Condition ──────────────────────────────────────────────────────────

export const ReturnConditionVariants: Record<ReturnCondition, BadgeVariant> = {
  GOOD: 'success',
  MINOR_DAMAGE: 'warning',
  MINOR_DAMAGE_REPAIR_REQUIRED: 'warning',
  MAJOR_DAMAGE: 'danger',
}

// ── Reset Status ──────────────────────────────────────────────────────────────

export const ResetStatusVariants: Record<ResetStatus, BadgeVariant> = {
  COMPLETE: 'success',
  INCOMPLETE: 'danger',
}

// ── Return Status ─────────────────────────────────────────────────────────────

export const ReturnStatusVariants: Record<ReturnStatus, BadgeVariant> = {
  RETURN_PENDING: 'warning',
  COMPLETED: 'success',
}

// ── Finance Notification Status ───────────────────────────────────────────────

export const FinanceNotificationStatusVariants: Record<
  FinanceNotificationStatus,
  BadgeVariant
> = {
  QUEUED: 'warning',
  COMPLETED: 'success',
  NO_FINANCE_USERS: 'warning',
  FAILED: 'danger',
}

// ── Risk Level ────────────────────────────────────────────────────────────────

export const RiskLevelVariants: Record<RiskLevel, BadgeVariant> = {
  LOW: 'success',
  MEDIUM: 'info',
  HIGH: 'danger',
}

// ── Data Access Impact ────────────────────────────────────────────────────────

export const DataAccessImpactVariants: Record<DataAccessImpact, BadgeVariant> =
{
  LOW: 'success',
  MEDIUM: 'info',
  HIGH: 'danger',
}

// ── Issue Category ────────────────────────────────────────────────────────────

export const IssueCategoryVariants: Record<IssueCategory, BadgeVariant> = {
  SOFTWARE: 'info',
  HARDWARE: 'warning',
}

// ── Notification Type ─────────────────────────────────────────────────────────

export const NotificationTypeVariants: Record<NotificationType, BadgeVariant> =
{
  // Action required
  ASSET_PENDING_APPROVAL: 'warning',
  REPLACEMENT_APPROVAL_NEEDED: 'warning',
  SOFTWARE_INSTALL_ESCALATION: 'warning',
  DISPOSAL_APPROVAL_NEEDED: 'warning',
  AUDIT_CONFIRMATION_REQUIRED: 'warning',
  AUDIT_REMINDER: 'warning',
  // Escalation
  AUDIT_DISPUTE_RAISED: 'warning',
  AUDIT_NON_RESPONSE_ESCALATION: 'warning',
  // Approved / success
  ASSET_APPROVED: 'success',
  REPLACEMENT_APPROVED: 'success',
  SOFTWARE_INSTALL_APPROVED: 'success',
  ISSUE_RESOLVED: 'success',
  HANDOVER_ACCEPTED: 'success',
  // Rejected
  ASSET_REJECTED: 'danger',
  REPLACEMENT_REJECTED: 'danger',
  SOFTWARE_INSTALL_REJECTED: 'danger',
  // Informational
  NEW_ISSUE_REPORTED: 'info',
  NEW_SOFTWARE_INSTALL_REQUEST: 'info',
  NEW_ASSET_ASSIGNED: 'info',
  HANDOVER_FORM_READY: 'info',
  ISSUE_UNDER_REPAIR: 'info',
  ISSUE_SENT_TO_WARRANTY: 'info',
  RETURN_INITIATED: 'info',
  ASSET_DISPOSED_WRITEOFF: 'info',
  REPLACEMENT_APPROVED_INFO: 'info',
  AUDIT_FINAL_ACKNOWLEDGEMENT: 'info',
  AUDIT_DISPUTE_REVIEWED: 'info',
}

// ── Maintenance Record Type ───────────────────────────────────────────────────

export const MaintenanceRecordTypeVariants: Record<
  MaintenanceRecordType,
  BadgeVariant
> = {
  ISSUE: 'danger',
  SOFTWARE_REQUEST: 'info',
  RETURN: 'warning',
  DISPOSAL: 'default',
}

// ── Asset Condition ───────────────────────────────────────────────────────────

export const AssetConditionVariants: Record<AssetCondition, BadgeVariant> = {
  GOOD: 'success',
  FAIR: 'warning',
  POOR: 'danger',
}

// ── User Status ───────────────────────────────────────────────────────────────

export const UserStatusVariants: Record<UserStatus, BadgeVariant> = {
  active: 'success',
  inactive: 'danger',
}

// ── Scan Status ───────────────────────────────────────────────────────────────

export const ScanStatusVariants: Record<ScanStatus, BadgeVariant> = {
  PROCESSING: 'warning',
  COMPLETED: 'success',
  SCAN_FAILED: 'danger',
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Resolve a status badge variant for maintenance history records,
 * where the `status` field is a plain string spanning multiple enum domains.
 */
export function getMaintenanceStatusVariant(
  recordType: MaintenanceRecordType,
  status: string,
): BadgeVariant {
  switch (recordType) {
    case 'ISSUE':
      return (
        (IssueStatusVariants as Record<string, BadgeVariant>)[status] ??
        'default'
      )
    case 'SOFTWARE_REQUEST':
      return (
        (SoftwareStatusVariants as Record<string, BadgeVariant>)[status] ??
        'default'
      )
    case 'RETURN':
      return (
        (ReturnStatusVariants as Record<string, BadgeVariant>)[status] ??
        (AssetStatusVariants as Record<string, BadgeVariant>)[status] ??
        'default'
      )
    case 'DISPOSAL':
      return (
        (AssetStatusVariants as Record<string, BadgeVariant>)[status] ??
        'default'
      )
  }
}
