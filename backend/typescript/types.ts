/**
 * TypeScript types for the Gadget Management System API.
 * Derived from Lambda function model.py files and utils/enums.py.
 */

import { z } from "zod"

// ---------------------------------------------------------------------------
// Enums (Zod schemas — single source of truth, mirrors utils/enums.py)
// ---------------------------------------------------------------------------

export const AssetStatusSchema = z.enum([
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
])
export type AssetStatus = z.infer<typeof AssetStatusSchema>

export const IssueStatusSchema = z.enum([
    "TROUBLESHOOTING",
    "UNDER_REPAIR",
    "SEND_WARRANTY",
    "RESOLVED",
    "REPLACEMENT_REQUIRED",
    "REPLACEMENT_APPROVED",
    "REPLACEMENT_REJECTED",
])
export type IssueStatus = z.infer<typeof IssueStatusSchema>

export const SoftwareStatusSchema = z.enum([
    "PENDING_REVIEW",
    "ESCALATED_TO_MANAGEMENT",
    "SOFTWARE_INSTALL_APPROVED",
    "SOFTWARE_INSTALL_REJECTED",
])
export type SoftwareStatus = z.infer<typeof SoftwareStatusSchema>

export const ScanStatusSchema = z.enum(["PROCESSING", "COMPLETED", "SCAN_FAILED"])
export type ScanStatus = z.infer<typeof ScanStatusSchema>

export const UserStatusSchema = z.enum(["active", "inactive"])
export type UserStatus = z.infer<typeof UserStatusSchema>

export const UserRoleSchema = z.enum(["it-admin", "management", "employee", "finance"])
export type UserRole = z.infer<typeof UserRoleSchema>

export const ReturnConditionSchema = z.enum([
    "GOOD",
    "MINOR_DAMAGE",
    "MINOR_DAMAGE_REPAIR_REQUIRED",
    "MAJOR_DAMAGE",
])
export type ReturnCondition = z.infer<typeof ReturnConditionSchema>

export const ResetStatusSchema = z.enum(["COMPLETE", "INCOMPLETE"])
export type ResetStatus = z.infer<typeof ResetStatusSchema>

export const ReturnTriggerSchema = z.enum([
    "RESIGNATION",
    "REPLACEMENT",
    "TRANSFER",
    "IT_RECALL",
    "UPGRADE",
])
export type ReturnTrigger = z.infer<typeof ReturnTriggerSchema>

export const ReturnStatusSchema = z.enum(["RETURN_PENDING", "COMPLETED"])
export type ReturnStatus = z.infer<typeof ReturnStatusSchema>

export const FinanceNotificationStatusSchema = z.enum([
    "QUEUED",
    "COMPLETED",
    "NO_FINANCE_USERS",
    "FAILED",
])
export type FinanceNotificationStatus = z.infer<typeof FinanceNotificationStatusSchema>

export const AssetConditionSchema = z.enum(["GOOD", "FAIR", "POOR"])
export type AssetCondition = z.infer<typeof AssetConditionSchema>

export const IssueCategorySchema = z.enum(["SOFTWARE", "HARDWARE"])
export type IssueCategory = z.infer<typeof IssueCategorySchema>

export const DataAccessImpactSchema = z.enum(["LOW", "MEDIUM", "HIGH"])
export type DataAccessImpact = z.infer<typeof DataAccessImpactSchema>

export const RiskLevelSchema = z.enum(["LOW", "MEDIUM", "HIGH"])
export type RiskLevel = z.infer<typeof RiskLevelSchema>

export const FileManifestItemTypeSchema = z.enum(["invoice", "gadget_photo"])
export type FileManifestItemType = z.infer<typeof FileManifestItemTypeSchema>

export const ReturnFileManifestItemTypeSchema = z.enum(["photo", "admin-signature"])
export type ReturnFileManifestItemType = z.infer<typeof ReturnFileManifestItemTypeSchema>

export const DocumentTypeSchema = z.enum(["handover", "return"])
export type DocumentType = z.infer<typeof DocumentTypeSchema>

export const ApproveRejectDecisionSchema = z.enum(["APPROVE", "REJECT"])
export type ApproveRejectDecision = z.infer<typeof ApproveRejectDecisionSchema>

export const ReviewDecisionSchema = z.enum(["APPROVE", "ESCALATE", "REJECT"])
export type ReviewDecision = z.infer<typeof ReviewDecisionSchema>

export const SortOrderSchema = z.enum(["asc", "desc"])
export type SortOrder = z.infer<typeof SortOrderSchema>

// ---------------------------------------------------------------------------
// Shared / Reusable
// ---------------------------------------------------------------------------

export type PaginatedAPIFilter = {
    page_size?: number
    cursor?: string
}

export type PaginatedAPIResponse<T> = {
    items: T[]
    count: number
    next_cursor: string | null
    has_next_page: boolean
}

export type AssetSpecs = {
    brand?: string
    model?: string
    serial_number?: string
    product_description?: string
    cost?: number
    purchase_date?: string
}

export type ExtractedFieldValue = {
    value?: string
    confidence?: number
    alternative_value?: string
    alternative_confidence?: number
}

// ---------------------------------------------------------------------------
// Upload URLs
// ---------------------------------------------------------------------------

export type FileManifestItem = {
    name: string
    content_type: string
    type: FileManifestItemType
}

export type GenerateUploadUrlsRequest = {
    files: FileManifestItem[]
}

export type PresignedUrlItem = {
    file_key: string
    presigned_url: string
    type: string
}

export type GenerateUploadUrlsResponse = {
    upload_session_id: string
    scan_job_id: string
    urls: PresignedUrlItem[]
}

// ---------------------------------------------------------------------------
// Asset Scan
// ---------------------------------------------------------------------------

export type GetScanResultsResponse = {
    status: ScanStatus
    extracted_fields?: Record<string, ExtractedFieldValue>
    failure_reason?: string
}

// ---------------------------------------------------------------------------
// Create Asset
// ---------------------------------------------------------------------------

export type CreateAssetRequest = {
    scan_job_id: string
    invoice_number: string
    vendor: string
    purchase_date: string
    brand: string
    model_name: string
    cost: number
    category: string
    serial_number?: string
    product_description?: string
    payment_method?: string
    processor?: string
    storage?: string
    os_version?: string
    memory?: string
}

export type CreateAssetResponse = {
    asset_id: string
    status: AssetStatus
}

// ---------------------------------------------------------------------------
// Get Asset
// ---------------------------------------------------------------------------

export type AssigneeInfo = {
    user_id: string
    fullname: string
    role: UserRole
}

export type GetAssetResponse = {
    asset_id: string
    invoice_number?: string
    vendor?: string
    purchase_date?: string
    serial_number?: string
    brand?: string
    model?: string
    product_description?: string
    cost?: number
    payment_method?: string
    processor?: string
    storage?: string
    os_version?: string
    memory?: string
    invoice_url?: string
    gadget_photo_urls?: string[]
    status: AssetStatus
    category?: string
    condition?: AssetCondition
    remarks?: string
    rejection_reason?: string
    created_at?: string
    assigned_date?: string
    assignee?: AssigneeInfo
}

// ---------------------------------------------------------------------------
// Approve Asset
// ---------------------------------------------------------------------------

export type ApproveAssetRequest = {
    action: ApproveRejectDecision
    remarks?: string
    rejection_reason?: string
}

export type ApproveAssetResponse = {
    asset_id: string
    status: AssetStatus
}

// ---------------------------------------------------------------------------
// Assign Asset
// ---------------------------------------------------------------------------

export type AssignAssetRequest = {
    employee_id: string
    notes?: string
}

export type AssignAssetResponse = {
    asset_id: string
    employee_id: string
    assignment_date: string
    status: AssetStatus
    presigned_url: string
}

// ---------------------------------------------------------------------------
// Cancel Assignment
// ---------------------------------------------------------------------------

export type CancelAssignmentResponse = {
    asset_id: string
    status: AssetStatus
}

// ---------------------------------------------------------------------------
// Handover
// ---------------------------------------------------------------------------

export type GetHandoverFormResponse = {
    asset_id: string
    presigned_url: string
}

export type GetSignedHandoverFormResponse = {
    asset_id: string
    presigned_url: string
}

export type GenerateSignatureUploadUrlResponse = {
    presigned_url: string
    s3_key: string
    asset_id: string
}

export type AcceptHandoverRequest = {
    signature_s3_key: string
}

export type AcceptHandoverResponse = {
    asset_id: string
    status: AssetStatus
    signed_form_url: string
}

// ---------------------------------------------------------------------------
// List Assets
// ---------------------------------------------------------------------------

export type ListAssetsFilter = PaginatedAPIFilter & {
    status?: AssetStatus
    category?: string
    brand?: string
    model_name?: string
    date_from?: string
    date_to?: string
}

export type AssetItem = {
    asset_id: string
    brand?: string
    model?: string
    serial_number?: string
    status: AssetStatus
    category?: string
    assignment_date?: string
    condition?: AssetCondition
    created_at?: string
}

export type ListAssetsResponse = PaginatedAPIResponse<AssetItem>

// ---------------------------------------------------------------------------
// Asset Categories
// ---------------------------------------------------------------------------

export type CategoryItem = {
    category_id: string
    category_name: string
    created_at: string
}

export type CreateAssetCategoryRequest = {
    category_name: string
}

export type CreateAssetCategoryResponse = {
    category_id: string
    category_name: string
    created_at: string
}

export type ListAssetCategoriesResponse = PaginatedAPIResponse<CategoryItem>

// ---------------------------------------------------------------------------
// Return
// ---------------------------------------------------------------------------

export type InitiateReturnRequest = {
    return_trigger: ReturnTrigger
    remarks: string
    condition_assessment: ReturnCondition
    reset_status: ResetStatus
}

export type InitiateReturnResponse = {
    asset_id: string
    return_id: string
    status: AssetStatus
}

export type ReturnFileManifestItem = {
    name: string
    type: ReturnFileManifestItemType  // "photo" | "admin-signature"
    content_type?: string
}

export type GenerateReturnUploadUrlsRequest = {
    files: ReturnFileManifestItem[]
}

export type ReturnPresignedUrlItem = {
    file_key: string
    presigned_url: string
    type: string
    content_type: string
}

export type GenerateReturnUploadUrlsResponse = {
    upload_urls: ReturnPresignedUrlItem[]
}

export type SubmitAdminReturnEvidenceResponse = {
    asset_id: string
    return_id: string
    message: string
}

export type GenerateReturnSignatureUploadUrlRequest = {
    file_name: string
}

export type GenerateReturnSignatureUploadUrlResponse = {
    presigned_url: string
    s3_key: string
    return_id: string
    asset_id: string
}

// Employee submits their signature key to complete the return
export type CompleteReturnRequest = {
    user_signature_s3_key: string
}

export type CompleteReturnResponse = {
    asset_id: string
    new_status: AssetStatus
    completed_at: string
}

export type GetReturnResponse = {
    asset_id: string
    return_id: string
    return_trigger: ReturnTrigger
    initiated_by: string
    initiated_by_id: string
    initiated_at: string
    // Set at initiation
    condition_assessment: ReturnCondition
    remarks: string
    reset_status: ResetStatus
    serial_number?: string
    model?: string
    // Admin evidence
    return_photo_urls?: string[]
    admin_signature_url?: string
    // Employee evidence
    user_signature_url?: string
    completed_at?: string
    completed_by?: string
    completed_by_id?: string
    resolved_status?: ReturnStatus
    asset_status: AssetStatus
}

export type ListReturnsFilter = PaginatedAPIFilter & {
    return_trigger?: ReturnTrigger
    condition_assessment?: ReturnCondition
}

export type ReturnListItem = {
    asset_id: string
    return_id: string
    return_trigger: ReturnTrigger
    initiated_by: string
    initiated_by_id: string
    initiated_at: string
    condition_assessment: ReturnCondition
    remarks: string
    reset_status: ResetStatus
    resolved_status?: ReturnStatus
    completed_at?: string
}

export type ListReturnsResponse = PaginatedAPIResponse<ReturnListItem>

// ---------------------------------------------------------------------------
// List All Returns (IT Admin — global)
// ---------------------------------------------------------------------------

export type ListAllReturnsFilter = PaginatedAPIFilter & {
    status?: ReturnStatus
    return_trigger?: ReturnTrigger
    condition_assessment?: ReturnCondition
}

export type AllReturnListItem = {
    asset_id: string
    return_id: string
    return_trigger: ReturnTrigger
    initiated_by: string
    initiated_by_id: string
    initiated_at: string
    condition_assessment: ReturnCondition
    remarks: string
    reset_status: ResetStatus
    serial_number?: string
    model?: string
    resolved_status?: ReturnStatus
    completed_at?: string
    completed_by?: string
    completed_by_id?: string
}

export type ListAllReturnsResponse = PaginatedAPIResponse<AllReturnListItem>

// ---------------------------------------------------------------------------
// Employee Signatures
// ---------------------------------------------------------------------------

export type ListEmployeeSignaturesFilter = PaginatedAPIFilter & {
    assignment_date_from?: string
    assignment_date_to?: string
}

export type SignatureItem = {
    asset_id: string
    brand?: string
    model?: string
    assignment_date: string
    signature_timestamp: string
    signature_url: string
}

export type ListEmployeeSignaturesResponse = PaginatedAPIResponse<SignatureItem>

// ---------------------------------------------------------------------------
// Pending Signatures
// ---------------------------------------------------------------------------

export type PendingSignatureItem = {
    document_type: DocumentType
    asset_id: string
    record_id: string
    // handover-specific
    employee_name?: string
    assignment_date?: string
    handover_form_s3_key?: string
    // return-specific
    return_trigger?: ReturnTrigger
    initiated_at?: string
}

export type ListPendingSignaturesResponse = PaginatedAPIResponse<PendingSignatureItem>

// ---------------------------------------------------------------------------
// Issues
// ---------------------------------------------------------------------------

export type SubmitIssueRequest = {
    issue_description: string
    category: IssueCategory
}

export type SubmitIssueResponse = {
    asset_id: string
    issue_id: string
    status: IssueStatus
}

// Issue Upload URLs

export type IssueFileManifestItem = {
    name: string
    type: "photo"
    content_type: string
}

export type GenerateIssueUploadUrlsRequest = {
    files: IssueFileManifestItem[]
}

export type IssuePresignedUrlItem = {
    file_key: string
    presigned_url: string
    type: string
    content_type: string
}

export type GenerateIssueUploadUrlsResponse = {
    upload_urls: IssuePresignedUrlItem[]
}

export type ListIssuesFilter = PaginatedAPIFilter & {
    status?: IssueStatus
}

export type IssueListItem = {
    asset_id: string
    issue_id: string
    issue_description: string
    category: IssueCategory
    status: IssueStatus
    action_path?: string
    reported_by: string
    reported_by_id: string
    created_at: string
    issue_photo_urls?: string[]
    resolved_by?: string
    resolved_by_id?: string
    resolved_at?: string
    repair_notes?: string
    warranty_notes?: string
    warranty_sent_at?: string
    replacement_justification?: string
    management_reviewed_by?: string
    management_reviewed_by_id?: string
    management_reviewed_at?: string
    management_rejection_reason?: string
    management_remarks?: string
    completed_at?: string
    completion_notes?: string
}

export type ListIssuesResponse = PaginatedAPIResponse<IssueListItem>

export type GetIssueResponse = IssueListItem

export type SendWarrantyRequest = {
    warranty_notes?: string
}

export type SendWarrantyResponse = {
    asset_id: string
    issue_id: string
    status: IssueStatus
}

export type RequestReplacementRequest = {
    replacement_justification: string
}

export type RequestReplacementResponse = {
    asset_id: string
    issue_id: string
    status: IssueStatus
}

export type ManagementReviewIssueRequest = {
    decision: ApproveRejectDecision
    remarks?: string
    rejection_reason?: string
}

export type ManagementReviewIssueResponse = {
    asset_id: string
    issue_id: string
    status: IssueStatus
}

export type ListPendingReplacementsFilter = PaginatedAPIFilter

export type PendingReplacementListItem = {
    asset_id: string
    issue_id: string
    issue_description: string
    action_path?: string
    reported_by: string
    reported_by_id: string
    created_at: string
    resolved_by?: string
    resolved_by_id?: string
    resolved_at?: string
    replacement_justification?: string
    status: IssueStatus
}

export type ListPendingReplacementsResponse = PaginatedAPIResponse<PendingReplacementListItem>

// ---------------------------------------------------------------------------
// Repair
// ---------------------------------------------------------------------------

export type ResolveRepairRequest = {
    repair_notes?: string
}

export type ResolveRepairResponse = {
    asset_id: string
    issue_id: string
    status: IssueStatus
}

export type CompleteRepairRequest = {
    completion_notes?: string
}

export type CompleteRepairResponse = {
    asset_id: string
    issue_id: string
    status: IssueStatus
}

// ---------------------------------------------------------------------------
// Software Requests
// ---------------------------------------------------------------------------

export type SubmitSoftwareRequestRequest = {
    software_name: string
    version: string
    vendor: string
    justification: string
    license_type: string
    license_validity_period: string
    data_access_impact: DataAccessImpact
}

export type SubmitSoftwareRequestResponse = {
    asset_id: string
    software_request_id: string
    status: SoftwareStatus
}

export type ReviewSoftwareRequestRequest = {
    decision: ReviewDecision
    risk_level: RiskLevel
    rejection_reason?: string
}

export type ReviewSoftwareRequestResponse = {
    asset_id: string
    software_request_id: string
    status: SoftwareStatus
    risk_level: RiskLevel
}

export type ManagementReviewSoftwareRequestRequest = {
    decision: ApproveRejectDecision
    rejection_reason?: string
    remarks?: string
}

export type ManagementReviewSoftwareRequestResponse = {
    asset_id: string
    software_request_id: string
    status: SoftwareStatus
}

export type GetSoftwareRequestResponse = {
    asset_id: string
    software_request_id: string
    software_name: string
    version: string
    vendor: string
    justification: string
    license_type: string
    license_validity_period: string
    data_access_impact: string
    status: SoftwareStatus
    risk_level?: RiskLevel
    requested_by: string
    requested_by_id: string
    reviewed_by?: string
    reviewed_by_id?: string
    reviewed_at?: string
    rejection_reason?: string
    management_reviewed_by?: string
    management_reviewed_by_id?: string
    management_reviewed_at?: string
    management_rejection_reason?: string
    management_remarks?: string
    created_at: string
    installation_timestamp?: string
}

export type ListSoftwareRequestsFilter = PaginatedAPIFilter & {
    status?: SoftwareStatus
    risk_level?: RiskLevel
    software_name?: string
    vendor?: string
    license_validity_period?: string
    data_access_impact?: DataAccessImpact
}

export type SoftwareRequestListItem = {
    asset_id: string
    software_request_id: string
    software_name: string
    version: string
    vendor: string
    justification: string
    license_type: string
    license_validity_period: string
    data_access_impact: string
    status: SoftwareStatus
    risk_level?: RiskLevel
    requested_by: string
    requested_by_id: string
    reviewed_by?: string
    reviewed_by_id?: string
    rejection_reason?: string
    created_at: string
    reviewed_at?: string
}

export type ListSoftwareRequestsResponse = PaginatedAPIResponse<SoftwareRequestListItem>

export type ListAllSoftwareRequestsFilter = PaginatedAPIFilter & {
    status?: SoftwareStatus
    risk_level?: RiskLevel
    software_name?: string
    vendor?: string
}

export type AllSoftwareRequestListItem = {
    asset_id: string
    software_request_id: string
    software_name: string
    version: string
    vendor: string
    justification: string
    license_type: string
    license_validity_period: string
    data_access_impact: string
    status: SoftwareStatus
    risk_level?: RiskLevel
    requested_by: string
    requested_by_id: string
    reviewed_by?: string
    reviewed_by_id?: string
    rejection_reason?: string
    created_at: string
    reviewed_at?: string
    management_reviewed_by?: string
    management_reviewed_by_id?: string
    management_reviewed_at?: string
    management_rejection_reason?: string
    management_remarks?: string
}

export type ListAllSoftwareRequestsResponse = PaginatedAPIResponse<AllSoftwareRequestListItem>

// ---------------------------------------------------------------------------
// All Issues (IT admin — across all assets)
// ---------------------------------------------------------------------------

export type ListAllIssuesFilter = PaginatedAPIFilter & {
    status?: IssueStatus
    category?: IssueCategory
    sort_order?: SortOrder
}

export type AllIssueListItem = {
    asset_id: string
    issue_id: string
    issue_description: string
    category: IssueCategory
    status: IssueStatus
    action_path?: string
    reported_by: string
    reported_by_id: string
    created_at: string
    resolved_by?: string
    resolved_by_id?: string
    resolved_at?: string
    repair_notes?: string
    warranty_notes?: string
    warranty_sent_at?: string
    replacement_justification?: string
    management_reviewed_by?: string
    management_reviewed_by_id?: string
    management_reviewed_at?: string
    management_rejection_reason?: string
    management_remarks?: string
    completed_at?: string
    completion_notes?: string
}

export type ListAllIssuesResponse = PaginatedAPIResponse<AllIssueListItem>

// ---------------------------------------------------------------------------
// Disposal
// ---------------------------------------------------------------------------

export type InitiateDisposalRequest = {
    disposal_reason: string
    justification: string
}

export type InitiateDisposalResponse = {
    asset_id: string
    disposal_id: string
    status: AssetStatus
}

export type ManagementReviewDisposalRequest = {
    decision: ApproveRejectDecision
    remarks?: string
    rejection_reason?: string
}

export type ManagementReviewDisposalResponse = {
    asset_id: string
    disposal_id: string
    status: AssetStatus
}

export type CompleteDisposalRequest = {
    disposal_date: string
    data_wipe_confirmed: boolean
}

export type CompleteDisposalResponse = {
    asset_id: string
    disposal_id: string
    status: AssetStatus
    finance_notification_status: FinanceNotificationStatus
}

export type GetDisposalDetailsResponse = {
    asset_id: string
    disposal_id: string
    status: AssetStatus
    disposal_reason: string
    justification: string
    asset_specs?: AssetSpecs
    initiated_by: string
    initiated_by_id: string
    initiated_at: string
    management_reviewed_by?: string
    management_reviewed_by_id?: string
    management_reviewed_at?: string
    management_approved_at?: string
    management_rejection_reason?: string
    management_remarks?: string
    disposal_date?: string
    data_wipe_confirmed?: boolean
    completed_by?: string
    completed_by_id?: string
    completed_at?: string
    is_locked: boolean
    finance_notified_at?: string
    finance_notification_sent: boolean
    finance_notification_status?: FinanceNotificationStatus
}

export type ListDisposalsFilter = PaginatedAPIFilter & {
    disposal_reason?: string
    date_from?: string
    date_to?: string
}

export type DisposalListItem = {
    asset_id: string
    disposal_id: string
    disposal_reason: string
    justification: string
    initiated_by: string
    initiated_by_id: string
    initiated_at: string
    status: AssetStatus
    management_reviewed_by?: string
    management_reviewed_by_id?: string
    management_reviewed_at?: string
    management_rejection_reason?: string
    disposal_date?: string
    data_wipe_confirmed?: boolean
}

export type ListDisposalsResponse = PaginatedAPIResponse<DisposalListItem>

export type ListPendingDisposalsFilter = PaginatedAPIFilter & {
    disposal_reason?: string
}

export type PendingDisposalItem = {
    asset_id: string
    disposal_id: string
    disposal_reason: string
    justification: string
    asset_specs?: AssetSpecs
    initiated_by: string
    initiated_by_id: string
    initiated_at: string
}

export type ListPendingDisposalsResponse = PaginatedAPIResponse<PendingDisposalItem>

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

export type CreateUserRequest = {
    fullname: string
    email: string
    role: UserRole
    initial_password: string
}

export type CreateUserResponse = {
    user_id: string
    role: UserRole
    status: UserStatus
}

export type DeactivateUserResponse = {
    user_id: string
    status: UserStatus
    message: string
}

export type ListUsersFilter = PaginatedAPIFilter & {
    role?: UserRole
    status?: UserStatus
    name?: string
}

export type UserItem = {
    user_id: string
    fullname: string
    email: string
    role: UserRole
    status: UserStatus
    created_at: string
}

export type ListUsersResponse = PaginatedAPIResponse<UserItem>

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

export const NotificationTypeSchema = z.enum([
    "ASSET_PENDING_APPROVAL",
    "REPLACEMENT_APPROVAL_NEEDED",
    "SOFTWARE_INSTALL_ESCALATION",
    "DISPOSAL_APPROVAL_NEEDED",
    "ASSET_APPROVED",
    "ASSET_REJECTED",
    "NEW_ISSUE_REPORTED",
    "REPLACEMENT_APPROVED",
    "REPLACEMENT_REJECTED",
    "NEW_SOFTWARE_INSTALL_REQUEST",
    "HANDOVER_ACCEPTED",
    "AUDIT_DISPUTE_RAISED",
    "AUDIT_NON_RESPONSE_ESCALATION",
    "NEW_ASSET_ASSIGNED",
    "HANDOVER_FORM_READY",
    "SOFTWARE_INSTALL_APPROVED",
    "SOFTWARE_INSTALL_REJECTED",
    "ISSUE_UNDER_REPAIR",
    "ISSUE_SENT_TO_WARRANTY",
    "ISSUE_RESOLVED",
    "RETURN_INITIATED",
    "AUDIT_CONFIRMATION_REQUIRED",
    "AUDIT_FINAL_ACKNOWLEDGEMENT",
    "AUDIT_DISPUTE_REVIEWED",
    "AUDIT_REMINDER",
    "ASSET_DISPOSED_WRITEOFF",
    "REPLACEMENT_APPROVED_INFO",
])
export type NotificationType = z.infer<typeof NotificationTypeSchema>

export const ReferenceTypeSchema = z.enum([
    "ASSET", "ISSUE", "SOFTWARE", "DISPOSAL", "AUDIT", "RETURN",
])
export type ReferenceType = z.infer<typeof ReferenceTypeSchema>

export type NotificationItem = {
    notification_id: string
    notification_type: NotificationType
    title: string
    message: string
    reference_id: string
    reference_type: ReferenceType
    is_read: boolean
    created_at: string
}

export type ListNotificationsFilter = PaginatedAPIFilter & {
    is_read?: boolean
}

export type ListNotificationsResponse = PaginatedAPIResponse<NotificationItem> & {
    unread_count: number
}

export type MarkNotificationReadResponse = {
    notification_id: string
    notification_type: NotificationType
    title: string
    message: string
    reference_id: string
    reference_type: ReferenceType
    is_read: boolean
    created_at: string
}

// ---------------------------------------------------------------------------
// Dashboard Counters
// ---------------------------------------------------------------------------

export type GetDashboardCountersResponse = {
    AssetCount: number
    IssueCount: number
    ReturnCount: number
    DisposalCount: number
    AssignmentCount: number
    SoftwareRequestCount: number
}

// ---------------------------------------------------------------------------
// WebSocket Notifications
// ---------------------------------------------------------------------------

export type WebSocketNotificationPayload = {
    notification_type: NotificationType
    title: string
    message: string
    reference_id: string
    reference_type: ReferenceType
}

export type WebSocketMessage = {
    type: "notification"
    data: WebSocketNotificationPayload
}
