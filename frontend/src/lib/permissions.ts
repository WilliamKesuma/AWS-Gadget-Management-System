import type {
  AssetStatus,
  IssueStatus,
  SoftwareStatus,
  UserRole,
} from './models/types'

// ---------------------------------------------------------------------------
// Core helpers
// ---------------------------------------------------------------------------

/** Check if the current role is in the allowed list */
export function hasRole(role: UserRole | null, allowed: UserRole[]): boolean {
  return role != null && allowed.includes(role)
}

/** Check if the current user owns the resource */
export function isOwner(
  currentUserId: string | null,
  resourceOwnerId: string | undefined,
): boolean {
  return (
    currentUserId != null &&
    resourceOwnerId != null &&
    currentUserId === resourceOwnerId
  )
}

// ---------------------------------------------------------------------------
// Asset Detail permissions
// ---------------------------------------------------------------------------

export type AssetDetailContext = {
  role: UserRole | null
  currentUserId: string | null
  assigneeUserId: string | undefined
  assetStatus: AssetStatus | undefined
}

export type AssetDetailPermissions = {
  showSoftwareRequestsTab: boolean
  showIssuesTab: boolean
  showReportIssueButton: boolean
  showRequestSoftwareButton: boolean
  showInitiateReturnButton: boolean
  showReturnsTab: boolean
  showDisposalsTab: boolean
  showInitiateDisposalButton: boolean
  canInitiateDisposalAction: boolean
  showManagementReviewButton: boolean
  showLogsTab: boolean
}

export function getAssetDetailPermissions(
  ctx: AssetDetailContext,
): AssetDetailPermissions {
  const { role, currentUserId, assigneeUserId, assetStatus } = ctx
  const isAssignee = isOwner(currentUserId, assigneeUserId)
  const isAssigned = assetStatus === 'ASSIGNED'

  return {
    showSoftwareRequestsTab:
      hasRole(role, ['it-admin']) ||
      (hasRole(role, ['employee']) && isAssignee),
    showIssuesTab:
      hasRole(role, ['it-admin', 'management']) ||
      (hasRole(role, ['employee']) && isAssignee),
    showReportIssueButton:
      hasRole(role, ['employee']) && isAssigned && isAssignee,
    showRequestSoftwareButton:
      hasRole(role, ['employee']) && isAssigned && isAssignee,
    showInitiateReturnButton: hasRole(role, ['it-admin']) && isAssigned,
    showReturnsTab: hasRole(role, ['it-admin']),
    showDisposalsTab: hasRole(role, ['it-admin', 'management']),
    showInitiateDisposalButton:
      hasRole(role, ['it-admin']) &&
      assetStatus != null &&
      DISPOSAL_ELIGIBLE_STATUSES.includes(assetStatus),
    canInitiateDisposalAction:
      hasRole(role, ['it-admin']) && assetStatus === 'DISPOSAL_REVIEW',
    showManagementReviewButton:
      hasRole(role, ['management']) && assetStatus === 'ASSET_PENDING_APPROVAL',
    showLogsTab: hasRole(role, ['it-admin', 'management']),
  }
}

// ---------------------------------------------------------------------------
// Issue Detail action permissions
// ---------------------------------------------------------------------------

export type IssueActionContext = {
  role: UserRole | null
  issueStatus: IssueStatus
}

export type IssueActionPermissions = {
  canStartRepair: boolean
  canRequestReplacement: boolean
  canSendWarranty: boolean
  canCompleteRepair: boolean
  canManagementReview: boolean
}

export function getIssueActionPermissions(
  ctx: IssueActionContext,
): IssueActionPermissions {
  const { role, issueStatus } = ctx
  const isAdmin = hasRole(role, ['it-admin'])

  return {
    canStartRepair: isAdmin && issueStatus === 'TROUBLESHOOTING',
    canRequestReplacement: isAdmin && issueStatus === 'TROUBLESHOOTING',
    canSendWarranty: isAdmin && issueStatus === 'UNDER_REPAIR',
    canCompleteRepair:
      isAdmin &&
      (issueStatus === 'UNDER_REPAIR' || issueStatus === 'SEND_WARRANTY'),
    canManagementReview:
      hasRole(role, ['management']) && issueStatus === 'REPLACEMENT_REQUIRED',
  }
}

// ---------------------------------------------------------------------------
// Software Request action permissions
// ---------------------------------------------------------------------------

export type SoftwareActionContext = {
  role: UserRole | null
  status: SoftwareStatus
}

export type SoftwareActionPermissions = {
  canITAdminReview: boolean
  canManagementReview: boolean
}

export function getSoftwareActionPermissions(
  ctx: SoftwareActionContext,
): SoftwareActionPermissions {
  return {
    canITAdminReview:
      hasRole(ctx.role, ['it-admin']) && ctx.status === 'PENDING_REVIEW',
    canManagementReview:
      hasRole(ctx.role, ['management']) &&
      ctx.status === 'ESCALATED_TO_MANAGEMENT',
  }
}

// ---------------------------------------------------------------------------
// Asset Row (list table) permissions
// ---------------------------------------------------------------------------

export type AssetRowContext = {
  role: UserRole | null
  assetStatus: AssetStatus
}

export type AssetRowPermissions = {
  canManagementReview: boolean
}

export function getAssetRowPermissions(
  ctx: AssetRowContext,
): AssetRowPermissions {
  return {
    canManagementReview:
      hasRole(ctx.role, ['management']) &&
      ctx.assetStatus === 'ASSET_PENDING_APPROVAL',
  }
}

// ---------------------------------------------------------------------------
// User Row permissions
// ---------------------------------------------------------------------------

export type UserRowContext = {
  currentRole: UserRole | null
  currentUserId: string | null
  targetUserId: string
  targetRole: UserRole
}

export type UserRowPermissions = {
  canViewSignatures: boolean
  canToggleStatus: boolean
}

export function getUserRowPermissions(ctx: UserRowContext): UserRowPermissions {
  const isSelf = isOwner(ctx.currentUserId, ctx.targetUserId)
  return {
    canViewSignatures:
      hasRole(ctx.currentRole, ['it-admin']) && ctx.targetRole === 'employee',
    canToggleStatus: !isSelf,
  }
}

// ---------------------------------------------------------------------------
// Return Detail permissions
// ---------------------------------------------------------------------------

export type ReturnDetailContext = {
  role: UserRole | null
  assetStatus: AssetStatus | undefined
  adminSignatureUrl: string | null | undefined
  userSignatureUrl: string | null | undefined
}

export type ReturnDetailPermissions = {
  canUploadEvidence: boolean
  canUploadPhotos: boolean
  canRenotifyEmployee: boolean
  canSignAndComplete: boolean
  canViewReturnsTab: boolean
}

export function getReturnDetailPermissions(
  ctx: ReturnDetailContext,
): ReturnDetailPermissions {
  const { role, assetStatus, adminSignatureUrl, userSignatureUrl } = ctx
  const isPending = assetStatus === 'RETURN_PENDING'

  return {
    canUploadEvidence:
      hasRole(role, ['it-admin']) && isPending && !adminSignatureUrl,
    canUploadPhotos:
      hasRole(role, ['it-admin']) && isPending && !!adminSignatureUrl,
    canRenotifyEmployee:
      hasRole(role, ['it-admin']) &&
      isPending &&
      !!adminSignatureUrl &&
      !userSignatureUrl,
    canSignAndComplete:
      hasRole(role, ['employee']) && isPending && !userSignatureUrl,
    canViewReturnsTab: hasRole(role, ['it-admin']),
  }
}

// ---------------------------------------------------------------------------
// Disposal Detail permissions
// ---------------------------------------------------------------------------

export type DisposalDetailContext = {
  role: UserRole | null
  assetStatus: AssetStatus | undefined
  managementApprovedAt: string | null | undefined
}

export type DisposalDetailPermissions = {
  canInitiateDisposal: boolean
  canManagementReview: boolean
  canCompleteDisposal: boolean
}

const DISPOSAL_ELIGIBLE_STATUSES: AssetStatus[] = [
  'DISPOSAL_REVIEW',
  'IN_STOCK',
  'DAMAGED',
  'REPAIR_REQUIRED',
]

export function getDisposalDetailPermissions(
  ctx: DisposalDetailContext,
): DisposalDetailPermissions {
  const { role, assetStatus, managementApprovedAt } = ctx

  return {
    canInitiateDisposal:
      hasRole(role, ['it-admin']) &&
      assetStatus != null &&
      DISPOSAL_ELIGIBLE_STATUSES.includes(assetStatus),
    canManagementReview:
      hasRole(role, ['management']) &&
      assetStatus === 'DISPOSAL_PENDING' &&
      !managementApprovedAt,
    canCompleteDisposal:
      hasRole(role, ['it-admin']) &&
      assetStatus === 'DISPOSAL_PENDING' &&
      !!managementApprovedAt,
  }
}