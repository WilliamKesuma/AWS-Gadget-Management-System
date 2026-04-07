# Frontend Migration Prompt — UUID-Based IDs & API Route Changes

## Context

This document describes **breaking changes** to the backend API that require frontend updates. These are not new features — they are corrections to existing Phase 3, 4, and 6 implementations. Apply these changes on top of the existing frontend codebase.

---

## Summary of Changes

1. **All entity IDs are now UUID v4** — `issue_id`, `return_id`, `disposal_id`, `software_request_id` are no longer ISO-8601 timestamps. They are UUID strings like `"3f2a1b4c-1234-4abc-8def-0123456789ab"`.
2. **API routes updated** — path parameters renamed from `{timestamp}` to their proper ID names.
3. **Disposal routes restructured** — disposal sub-actions now require `{disposal_id}` in the path.
4. **Triage step removed** — the `PUT .../triage` endpoint no longer exists. Issues start at `TROUBLESHOOTING` immediately on submission.
5. **New endpoints added** — `GET /issues/my`, `GET /assets/software-requests`, `GET /assets/software-requests/my`, `GET /assets/pending-returns`.
6. **`assigned_date` added** to `GetAssetResponse`.
7. **`category` field added** to issue submission and list responses.

---

## 1. Updated TypeScript Types

Replace all previous type definitions with the following. The key changes are:
- `timestamp` fields renamed to `issue_id`, `software_request_id`, `return_id`, `disposal_id`
- `triaged_by`, `triaged_by_id`, `triaged_at` removed from all issue types
- `category: IssueCategory` added to issue types
- `PaginatedAPIFilter` and `PaginatedAPIResponse<T>` are now explicitly defined

```ts
// Pagination base types
type PaginatedAPIFilter = {
    page?: number
    page_size?: number
}

type PaginatedAPIResponse<T> = {
    items: T[]
    count: number
    total_items: number
    total_pages: number
    current_page: number
}

// Issue category
type IssueCategory = "SOFTWARE" | "HARDWARE"

// Submit Issue
type SubmitIssueRequest = {
    issue_description: string
    category: IssueCategory
}

type SubmitIssueResponse = {
    asset_id: string
    issue_id: string       // UUID v4 — was "timestamp"
    status: IssueStatus
}

// Issue list item (used in ListIssues, ListAllIssues, ListMyIssues)
type IssueListItem = {
    asset_id: string
    issue_id: string       // UUID v4 — was "timestamp"
    issue_description: string
    category: IssueCategory
    status: IssueStatus
    action_path?: string
    reported_by: string
    reported_by_id: string
    created_at: string
    issue_photo_urls?: string[]
    // triaged_by / triaged_by_id / triaged_at REMOVED
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

type GetIssueResponse = IssueListItem

type ListIssuesResponse = PaginatedAPIResponse<IssueListItem>

// Issue action responses — all use issue_id now
type ResolveRepairResponse = { asset_id: string; issue_id: string; status: IssueStatus }
type SendWarrantyResponse = { asset_id: string; issue_id: string; status: IssueStatus }
type CompleteRepairResponse = { asset_id: string; issue_id: string; status: IssueStatus }
type RequestReplacementResponse = { asset_id: string; issue_id: string; status: IssueStatus }
type ManagementReviewIssueResponse = { asset_id: string; issue_id: string; status: IssueStatus }

// Pending replacements list item — triage fields removed
type PendingReplacementListItem = {
    asset_id: string
    issue_id: string       // UUID v4 — was "timestamp"
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

// Software request — software_request_id replaces timestamp
type SubmitSoftwareRequestResponse = {
    asset_id: string
    software_request_id: string   // UUID v4 — was "timestamp"
    status: SoftwareStatus
}

type SoftwareRequestListItem = {
    asset_id: string
    software_request_id: string   // UUID v4 — was "timestamp"
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

type GetSoftwareRequestResponse = {
    asset_id: string
    software_request_id: string   // UUID v4 — was "timestamp"
    // ... all other fields unchanged
}

type ReviewSoftwareRequestResponse = {
    asset_id: string
    software_request_id: string   // UUID v4 — was "timestamp"
    status: SoftwareStatus
    risk_level: RiskLevel
}

type ManagementReviewSoftwareRequestResponse = {
    asset_id: string
    software_request_id: string   // UUID v4 — was "timestamp"
    status: SoftwareStatus
}

// Disposal — disposal_id is now a UUID v4
type InitiateDisposalResponse = {
    asset_id: string
    disposal_id: string    // UUID v4
    status: AssetStatus
}

type ManagementReviewDisposalResponse = {
    asset_id: string
    disposal_id: string    // UUID v4
    status: AssetStatus
}

type CompleteDisposalResponse = {
    asset_id: string
    disposal_id: string    // UUID v4
    status: AssetStatus
    finance_notification_status: FinanceNotificationStatus
}

type GetDisposalDetailsResponse = {
    asset_id: string
    disposal_id: string    // UUID v4
    // ... all other fields unchanged
}

// Return — return_id is now a UUID v4
type InitiateReturnResponse = {
    asset_id: string
    return_id: string      // UUID v4
    status: AssetStatus
}

type GetReturnResponse = {
    asset_id: string
    return_id: string      // UUID v4
    // ... all other fields unchanged
}

// GetAsset — new field
type GetAssetResponse = {
    // ... all existing fields
    assigned_date?: string   // NEW — ISO-8601 date of assignment
}
```

---

## 2. Updated API Routes

### Phase 3 — Software Requests

| Before | After |
|--------|-------|
| `GET /assets/{asset_id}/software-requests/{timestamp}` | `GET /assets/{asset_id}/software-requests/{software_request_id}` |
| `PUT /assets/{asset_id}/software-requests/{timestamp}/review` | `PUT /assets/{asset_id}/software-requests/{software_request_id}/review` |
| `PUT /assets/{asset_id}/software-requests/{timestamp}/management-review` | `PUT /assets/{asset_id}/software-requests/{software_request_id}/management-review` |
| `GET /software-requests/escalated` | `GET /assets/software-requests` (with `status=ESCALATED_TO_MANAGEMENT` filter) |

New endpoints:
- `GET /assets/software-requests` — list all software requests across all assets (it-admin, management)
- `GET /assets/software-requests/my` — list the current employee's software requests across all assets (employee)

### Phase 4 — Issues

| Before | After |
|--------|-------|
| `GET /assets/{asset_id}/issues/{timestamp}` | `GET /assets/{asset_id}/issues/{issue_id}` |
| `POST /assets/{asset_id}/issues/{timestamp}/upload-urls` | `POST /assets/{asset_id}/issues/{issue_id}/upload-urls` |
| `PUT /assets/{asset_id}/issues/{timestamp}/triage` | **REMOVED** — no longer exists |
| `PUT /assets/{asset_id}/issues/{timestamp}/resolve-repair` | `PUT /assets/{asset_id}/issues/{issue_id}/resolve-repair` |
| `PUT /assets/{asset_id}/issues/{timestamp}/send-warranty` | `PUT /assets/{asset_id}/issues/{issue_id}/send-warranty` |
| `PUT /assets/{asset_id}/issues/{timestamp}/complete-repair` | `PUT /assets/{asset_id}/issues/{issue_id}/complete-repair` |
| `PUT /assets/{asset_id}/issues/{timestamp}/request-replacement` | `PUT /assets/{asset_id}/issues/{issue_id}/request-replacement` |
| `PUT /assets/{asset_id}/issues/{timestamp}/management-review` | `PUT /assets/{asset_id}/issues/{issue_id}/management-review` |

New endpoints:
- `GET /issues/my` — employee's own issues across all assets
- `GET /issues` — all issues across all assets (it-admin)
- `GET /assets/pending-returns` — assets with approved replacement issues awaiting return (it-admin)

### Phase 6 — Disposal

The disposal sub-action routes now require `{disposal_id}` in the path. The `disposal_id` is returned from `POST /assets/{asset_id}/disposals` and must be stored in frontend state.

| Before | After |
|--------|-------|
| `PUT /assets/{asset_id}/disposals/management-review` | `PUT /assets/{asset_id}/disposals/{disposal_id}/management-review` |
| `PUT /assets/{asset_id}/disposals/complete` | `PUT /assets/{asset_id}/disposals/{disposal_id}/complete` |
| `GET /assets/{asset_id}/disposals/details` | `GET /assets/{asset_id}/disposals/{disposal_id}` |

---

## 3. Triage Step Removed (Phase 4)

The `ISSUE_REPORTED` status on the **issue record** no longer exists. When an employee submits an issue:
- The **asset** status becomes `ISSUE_REPORTED`
- The **issue record** status starts at `TROUBLESHOOTING` immediately

**Remove from the frontend:**
- The "Triage Issue" button and confirmation dialog
- Any UI that shows `ISSUE_REPORTED` as an issue record status
- The triage section in the Issue Detail view (`triaged_by`, `triaged_by_id`, `triaged_at`)
- Any tab or filter that queries issues with `status=ISSUE_REPORTED`

**Update the issue status lifecycle display:**

```
Asset status: ISSUE_REPORTED (while any issue is open)
Issue record status flow:
  TROUBLESHOOTING → UNDER_REPAIR → RESOLVED
  TROUBLESHOOTING → UNDER_REPAIR → SEND_WARRANTY → RESOLVED
  TROUBLESHOOTING → REPLACEMENT_REQUIRED → REPLACEMENT_APPROVED / REPLACEMENT_REJECTED
```

The IT Admin now sees issues directly in `TROUBLESHOOTING` state and acts from there — no triage step.

---

## 4. Issue Category Field (Phase 4)

The `SubmitIssueRequest` now requires a `category` field. Update the Submit Issue form:

- Add a **Category** dropdown (required): `SOFTWARE` | `HARDWARE`
- Display `category` in the Issue Detail view and list tables

---

## 5. Disposal ID Persistence (Phase 6)

Since disposal sub-actions now require `{disposal_id}` in the URL, the frontend must persist the `disposal_id` after initiating a disposal.

When `POST /assets/{asset_id}/disposals` succeeds:
- Store the returned `disposal_id` in component state or route params
- Use it for all subsequent calls: management-review, complete, and get-details

The `disposal_id` is also returned in `GetDisposalDetailsResponse` and list responses, so it can be recovered from those if needed.

---

## 6. New: My Software Requests Page (Employee)

Replace the previous pattern of employees viewing software requests only through the asset detail page. Add a dedicated view accessible from navigation.

**Endpoint:** `GET /assets/software-requests/my`

Query params: `page`, `page_size`, `sort_order`, `status` (optional filter)

Display the same columns as the existing software requests list. Clicking a row navigates to the Software Request Detail page.

---

## 7. New: My Issues Page (Employee)

Add a dedicated view for employees to see all their issues across all assets.

**Endpoint:** `GET /issues/my`

Query params: `page`, `page_size`, `sort_order`, `status` (optional filter)

Display the same columns as the existing issues list. Clicking a row navigates to the Issue Detail page.

---

## 8. New: Pending Returns Page (IT Admin)

Add a page listing assets that have an approved replacement issue and are awaiting physical return.

**Endpoint:** `GET /assets/pending-returns`

Query params: `page`, `page_size`, `sort_order`

**Table columns:**

| Column | Field |
|--------|-------|
| Asset ID | `asset_id` |
| Brand | `brand` |
| Model | `model` |
| Serial Number | `serial_number` |
| Assigned To | `assignee_fullname` |
| Replacement Approved At | `replacement_approved_at` |
| Replacement Justification | `replacement_justification` |
| Actions | Link to issue detail (`issue_id`) |

---

## 9. Assigned Date on Asset Detail (Phase 2)

`GetAssetResponse` now includes `assigned_date`. Display it in the Asset Detail view when the asset is in `ASSIGNED` or `ISSUE_REPORTED` status.

---

## Migration Checklist

- [ ] Replace all `timestamp` references in API calls and state with the appropriate ID field (`issue_id`, `software_request_id`, `return_id`, `disposal_id`)
- [ ] Update all route path constructions: `/issues/${timestamp}` → `/issues/${issue_id}`, etc.
- [ ] Remove triage button, triage section, and `ISSUE_REPORTED` issue status handling
- [ ] Add `category` field to Submit Issue form and issue display components
- [ ] Update disposal flow to pass `disposal_id` through state for sub-action routes
- [ ] Replace `GET /software-requests/escalated` with `GET /assets/software-requests?status=ESCALATED_TO_MANAGEMENT`
- [ ] Add "My Issues" page for employees
- [ ] Add "My Software Requests" page for employees
- [ ] Add "Pending Returns" page for IT admins
- [ ] Display `assigned_date` on Asset Detail page
