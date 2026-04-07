# Frontend Implementation Prompt — Phase 4: Issue Management

## Context

You are building the React frontend for Phase 4 (Issue Management) of the Gadget Management System. The backend API is fully implemented. Every component and action described below must be conditionally rendered based on the user's role.

---

## API Endpoints

| Method | Path | Role(s) | Purpose |
| --- | --- | --- | --- |
| POST | `/assets/{asset_id}/issues` | employee | Submit an issue report for an assigned asset |
| GET | `/assets/{asset_id}/issues` | it-admin, employee | List issues for an asset (paginated, filterable) |
| GET | `/assets/{asset_id}/issues/{timestamp}` | it-admin, management, employee | View details of a specific issue |
| POST | `/assets/{asset_id}/issues/{timestamp}/upload-urls` | employee | Generate presigned URLs to upload issue evidence photos |
| PUT | `/assets/{asset_id}/issues/{timestamp}/triage` | it-admin | Triage issue (ISSUE\_REPORTED → TROUBLESHOOTING) |
| PUT | `/assets/{asset_id}/issues/{timestamp}/resolve-repair` | it-admin | Start repair — Option A (TROUBLESHOOTING → UNDER\_REPAIR) |
| PUT | `/assets/{asset_id}/issues/{timestamp}/send-warranty` | it-admin | Send to warranty (UNDER\_REPAIR → SEND\_WARRANTY) |
| PUT | `/assets/{asset_id}/issues/{timestamp}/complete-repair` | it-admin | Complete repair (UNDER\_REPAIR/SEND\_WARRANTY → RESOLVED, asset → ASSIGNED) |
| PUT | `/assets/{asset_id}/issues/{timestamp}/request-replacement` | it-admin | Request replacement — Option B (TROUBLESHOOTING → REPLACEMENT\_REQUIRED) |
| PUT | `/assets/{asset_id}/issues/{timestamp}/management-review` | management | Approve or reject replacement request |
| GET | `/issues/pending-replacements` | management | List all pending replacement requests across all assets (paginated) |

---

## TypeScript Types (already defined in `types.ts`)

```
// Enums
type IssueStatus =
    | "ISSUE_REPORTED"
    | "TROUBLESHOOTING"
    | "UNDER_REPAIR"
    | "SEND_WARRANTY"
    | "RESOLVED"
    | "REPLACEMENT_REQUIRED"
    | "REPLACEMENT_APPROVED"
    | "REPLACEMENT_REJECTED"

// Submit Issue
type SubmitIssueRequest = {
    issue_description: string
}

type SubmitIssueResponse = {
    asset_id: string
    timestamp: string
    status: IssueStatus
}

// Issue Upload URLs
type IssueFileManifestItem = {
    name: string
    type: "photo"
}

type GenerateIssueUploadUrlsRequest = {
    files: IssueFileManifestItem[]
}

type IssuePresignedUrlItem = {
    file_key: string
    presigned_url: string
    type: string
}

type GenerateIssueUploadUrlsResponse = {
    upload_urls: IssuePresignedUrlItem[]
}

// Triage Issue
type TriageIssueResponse = {
    asset_id: string
    timestamp: string
    status: IssueStatus
}

// Resolve Repair (Option A — start repair)
type ResolveRepairRequest = {
    repair_notes?: string
}

type ResolveRepairResponse = {
    asset_id: string
    timestamp: string
    status: IssueStatus
}

// Send Warranty
type SendWarrantyRequest = {
    warranty_notes?: string
}

type SendWarrantyResponse = {
    asset_id: string
    timestamp: string
    status: IssueStatus
}

// Complete Repair
type CompleteRepairRequest = {
    completion_notes?: string
}

type CompleteRepairResponse = {
    asset_id: string
    timestamp: string
    status: IssueStatus
}

// Request Replacement (Option B)
type RequestReplacementRequest = {
    replacement_justification: string
}

type RequestReplacementResponse = {
    asset_id: string
    timestamp: string
    status: IssueStatus
}

// Management Review Issue
type ManagementReviewIssueRequest = {
    decision: "APPROVE" | "REJECT"
    remarks?: string
    rejection_reason?: string
}

type ManagementReviewIssueResponse = {
    asset_id: string
    timestamp: string
    status: IssueStatus
}

// Get Issue Detail
type GetIssueResponse = {
    asset_id: string
    timestamp: string
    issue_description: string
    status: IssueStatus
    action_path?: string
    reported_by: string
    reported_by_id: string
    created_at: string
    issue_photo_urls?: string[]
    triaged_by?: string
    triaged_by_id?: string
    triaged_at?: string
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

// List Issues (per asset)
type ListIssuesFilter = PaginatedAPIFilter & {
    status?: IssueStatus
}

type IssueListItem = {
    asset_id: string
    timestamp: string
    issue_description: string
    status: IssueStatus
    action_path?: string
    reported_by: string
    reported_by_id: string
    created_at: string
    issue_photo_urls?: string[]
    triaged_by?: string
    triaged_by_id?: string
    triaged_at?: string
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

type ListIssuesResponse = PaginatedAPIResponse<IssueListItem>

// List Pending Replacements (management dashboard)
type ListPendingReplacementsFilter = PaginatedAPIFilter

type PendingReplacementListItem = {
    asset_id: string
    timestamp: string
    issue_description: string
    action_path: string
    reported_by: string
    reported_by_id: string
    created_at: string
    triaged_by: string
    triaged_by_id: string
    triaged_at: string
    resolved_by: string
    resolved_by_id: string
    resolved_at: string
    replacement_justification: string
    status: IssueStatus
}

type ListPendingReplacementsResponse = PaginatedAPIResponse<PendingReplacementListItem>
```

All paginated list responses follow this shape:

```
{ items: T[]; count: number; total_items: number; total_pages: number; current_page: number }
```

---

## Issue Status Lifecycle

```
ASSIGNED (asset status)
    │
    ▼  (Employee submits issue)
ISSUE_REPORTED (asset status only)
    │  issue record created with status: TROUBLESHOOTING
    ▼
TROUBLESHOOTING (issue record status)
    │
    ├── Option A: Repair ──────────────────┐
    │   ├── Repair (In House)              │
    │   │   ▼  (IT Admin starts repair)    │
    │   │   UNDER_REPAIR                   │
    │   │   ├── (IT Admin sends warranty)  │
    │   │   │   ▼                          │
    │   │   │   SEND_WARRANTY              │
    │   │   │   └── (IT Admin completes) ──┤
    │   │   └── (IT Admin completes) ──────┤
    │   └── Send Warranty directly ────────┤
    │                                      ▼
    │                                   RESOLVED (issue)
    │                                   ASSIGNED (asset restored)
    │
    └── Option B: Replacement ─────────────────────────────────────────────
        ▼  (IT Admin requests replacement)
        REPLACEMENT_REQUIRED
        ├── (Management approves) → REPLACEMENT_APPROVED
        └── (Management rejects)  → REPLACEMENT_REJECTED
```

The asset status is `ISSUE_REPORTED` for the entire duration of the issue. The issue record starts at `TROUBLESHOOTING` immediately on submission — there is no separate triage step. The IT Admin sees the issue in `TROUBLESHOOTING` state and decides the path from there.

The `action_path` field on the issue record indicates which resolution path was taken: `"REPAIR"` or `"REPLACEMENT"`. It is set when the IT Admin chooses Option A (resolve-repair) or Option B (request-replacement) from the TROUBLESHOOTING state.

---

## Features to Implement

### 1\. Submit Issue Report (Employee only)

**Render condition:** `role === "employee"` AND asset status is `ASSIGNED` AND the employee is the assigned user

On the Asset Detail page, show a "Report Issue" button.

Clicking it opens a modal/dialog with a form containing:

*   **Issue Description** — textarea (required, describe the problem with the asset)

On submit, call `POST /assets/{asset_id}/issues` with the `SubmitIssueRequest` body.

On success:

*   Show a success toast: "Issue reported successfully. IT Admin has been notified."
*   Close the modal and refresh the issues list for this asset.
*   The asset status will change to `ISSUE_REPORTED`.

Handle these error cases:

*   400 (ValidationError): Display the validation message. Common case: empty `issue_description`.
*   403: "You are not assigned to this asset" — the employee is not the assigned user.
*   404: "Asset not found" — the asset does not exist.
*   409: "Issues can only be reported for assets in ASSIGNED status" — the asset is not in ASSIGNED status.

> Note: On successful submission, the backend sends an email notification to all active IT Admin users via SES. This happens server-side — no frontend action needed.

---

### 2\. Upload Issue Evidence Photos (Employee only)

**Render condition:** `role === "employee"` AND the employee is the assigned user

After submitting an issue, the employee can upload evidence photos. This can be integrated into the Submit Issue flow (as a second step after submission) or available on the Issue Detail page.

**Step 1 — Generate presigned URLs:**

Prepare a file manifest with the photos to upload:

```
const request: GenerateIssueUploadUrlsRequest = {
    files: [
        { name: "crack-on-screen.jpg", type: "photo" },
        { name: "battery-swelling.jpg", type: "photo" }
    ]
}
```

Call `POST /assets/{asset_id}/issues/{timestamp}/upload-urls` with the request body.

The response contains presigned PUT URLs for each file.

**Step 2 — Upload files to S3:**

For each URL in the response, upload the file directly to S3:

```
await fetch(presignedUrl, {
    method: 'PUT',
    body: fileBlob,
    headers: { 'Content-Type': 'image/jpeg' }  // or image/png
})
```

Handle errors:

*   400: "At least one issue photo file is required" — empty files array.
*   403: "You are not assigned to this asset"
*   404: "Asset not found" or "Issue record not found"

On success, show a toast: "Photos uploaded successfully." The photos will appear as `issue_photo_urls` in the Issue Detail view.

---

### 3\. List Issues — /maintenance Page (IT Admin + Employee)

**Render condition:** `role === "it-admin"` OR (`role === "employee"` AND the employee is the assigned user)

This feature lives on a dedicated `/maintenance` page (not on the Asset Detail page). The page contains a tab component with three tabs. Each tab calls `GET /assets/{asset_id}/issues` with a pre-applied `status` filter — the user does not manually select a status filter.

**Tabs and their status filters:**

| Tab | Status filter(s) passed to API |
| --- | --- |
| Requests | `ISSUE_REPORTED` |
| Ongoing Repairs | `TROUBLESHOOTING`, `UNDER_REPAIR`, `SEND_WARRANTY`, `REPLACEMENT_REQUIRED`, `REPLACEMENT_APPROVED`, `REPLACEMENT_REJECTED` |
| Maintenance History | `RESOLVED` |

> For "Ongoing Repairs", since the API accepts a single `status` value per request, fetch each status separately and merge the results client-side, or use the most relevant status for the current view. Alternatively, if the backend supports multiple status values in the query param, pass them all at once.

**Table columns (shared across all tabs):**

| Column | Field | Notes |
| --- | --- | --- |
| Issue Description | `issue_description` | Truncate if long |
| Status | `status` | Render as a colored badge (see status badge colors below) |
| Action Path | `action_path` | Show "Repair", "Replacement", or "—" if not yet determined |
| Reported By | `reported_by` | Resolved user name |
| Created At | `created_at` | Formatted date |
| Actions | — | Link/button to view detail |

Include pagination controls per tab.

Handle errors:

*   403: "Insufficient permissions" or "You are not assigned to this asset"
*   404: "Asset not found"

If a tab has no issues, show a contextual empty state:

*   Requests tab: "No issues reported."
*   Ongoing Repairs tab: "No ongoing repairs."
*   Maintenance History tab: "No maintenance history."

---

### 4\. View Issue Detail (IT Admin + Management + Employee)

**Render condition:** `role === "it-admin"` OR `role === "management"` OR (`role === "employee"` AND the employee is the assigned user)

Clicking a row in the issues list (or navigating directly) opens a detail view.

Call `GET /assets/{asset_id}/issues/{timestamp}`.

**Display fields:**

| Section | Fields |
| --- | --- |
| Issue Info | `issue_description`, `action_path` (show "Repair", "Replacement", or "Pending Triage" if null) |
| Evidence Photos | `issue_photo_urls` — render as a gallery of clickable thumbnails. If empty/null, show "No photos attached." |
| Status | `status` (colored badge), `created_at`, `reported_by` |
| Triage | `triaged_by`, `triaged_at` (show only when populated) |
| Repair Details | `resolved_by`, `resolved_at`, `repair_notes`, `warranty_notes`, `warranty_sent_at`, `completed_at`, `completion_notes` (show only when action\_path is "REPAIR" and fields are populated) |
| Replacement Details | `replacement_justification`, `resolved_by`, `resolved_at` (show only when action\_path is "REPLACEMENT" and fields are populated) |
| Management Review | `management_reviewed_by`, `management_reviewed_at`, `management_rejection_reason`, `management_remarks` (show only when populated) |

**Conditional action buttons on the detail view:**

*   If `role === "it-admin"` AND `status === "TROUBLESHOOTING"` → Show "Repair" and "Replace" buttons (see Features 5 and 8)
*   If `role === "it-admin"` AND `status === "UNDER_REPAIR"` → Show "Send to Warranty" and "Complete Repair" buttons (see Features 7 and 8)
*   If `role === "it-admin"` AND `status === "SEND_WARRANTY"` → Show "Complete Repair" button (see Feature 8)
*   If `role === "management"` AND `status === "REPLACEMENT_REQUIRED"` → Show "Review Replacement" button (see Feature 10)

Handle errors:

*   403: "Insufficient permissions" or "You are not assigned to this asset"
*   404: "Asset not found" or "Issue record not found"

---

### 5\. Triage Issue (IT Admin only)

**Render condition:** `role === "it-admin"` AND issue status is `ISSUE_REPORTED`

On the Issue Detail page, show a "Triage Issue" button. This is a simple confirmation action — no form fields needed.

On click, show a confirmation dialog: "Acknowledge this issue and begin troubleshooting?"

On confirm, call `PUT /assets/{asset_id}/issues/{timestamp}/triage`.

On success:

*   Show toast: "Issue triaged. Status updated to Troubleshooting."
*   Refresh the detail view. Status becomes `TROUBLESHOOTING`.

Handle errors:

*   404: "Asset not found" or "Issue record not found"
*   409: "Asset is not in ISSUE\_REPORTED status" — the issue has already been triaged.

---

### 6\. Start Repair — Option A (IT Admin only)

**Render condition:** `role === "it-admin"` AND issue status is `TROUBLESHOOTING`

On the Issue Detail page, show a "Start Repair" button. Clicking it opens a modal/dialog with:

*   **Repair Notes** — textarea (optional, describe the repair plan)

On submit, call `PUT /assets/{asset_id}/issues/{timestamp}/resolve-repair` with the `ResolveRepairRequest` body.

On success:

*   Show toast: "Repair initiated. Status updated to Under Repair."
*   Refresh the detail view. Status becomes `UNDER_REPAIR`. The `action_path` is set to `"REPAIR"`.

Handle errors:

*   404: "Issue record not found"
*   409: "Issue is not in TROUBLESHOOTING status"

---

### 7\. Send to Warranty (IT Admin only)

**Render condition:** `role === "it-admin"` AND issue status is `UNDER_REPAIR`

On the Issue Detail page, show a "Send to Warranty" button. Clicking it opens a modal/dialog with:

*   **Warranty Notes** — textarea (optional, e.g. warranty claim reference number)

On submit, call `PUT /assets/{asset_id}/issues/{timestamp}/send-warranty` with the `SendWarrantyRequest` body.

On success:

*   Show toast: "Asset sent to warranty."
*   Refresh the detail view. Status becomes `SEND_WARRANTY`.

Handle errors:

*   404: "Issue record not found"
*   409: "Issue is not in UNDER\_REPAIR status"

---

### 8\. Complete Repair (IT Admin only)

**Render condition:** `role === "it-admin"` AND issue status is `UNDER_REPAIR` or `SEND_WARRANTY`

On the Issue Detail page, show a "Complete Repair" button. Clicking it opens a modal/dialog with:

*   **Completion Notes** — textarea (optional, describe what was done to resolve the issue)

On submit, call `PUT /assets/{asset_id}/issues/{timestamp}/complete-repair` with the `CompleteRepairRequest` body.

On success:

*   Show toast: "Repair completed. Asset restored to Assigned status."
*   Refresh the detail view. Issue status becomes `RESOLVED`. Asset status reverts to `ASSIGNED`.

Handle errors:

*   404: "Issue record not found"
*   409: "Issue is not in a repairable state" — the issue is not in UNDER\_REPAIR or SEND\_WARRANTY status.

---

### 9\. Request Replacement — Option B (IT Admin only)

**Render condition:** `role === "it-admin"` AND issue status is `TROUBLESHOOTING`

On the Issue Detail page, show a "Request Replacement" button. Clicking it opens a modal/dialog with:

*   **Replacement Justification** — textarea (required, explain why the asset needs to be replaced)

On submit, call `PUT /assets/{asset_id}/issues/{timestamp}/request-replacement` with the `RequestReplacementRequest` body.

On success:

*   Show toast: "Replacement request submitted. Management will review."
*   Refresh the detail view. Status becomes `REPLACEMENT_REQUIRED`. The `action_path` is set to `"REPLACEMENT"`.

Handle errors:

*   400 (ValidationError): "replacement\_justification must not be empty"
*   404: "Issue record not found"
*   409: "Issue is not in TROUBLESHOOTING status"

> Note: On successful submission, the backend sends an email notification to all active Management users via SES. This happens server-side — no frontend action needed.

---

### 10\. Management Review of Replacement Request (Management only)

**Render condition:** `role === "management"` AND issue status is `REPLACEMENT_REQUIRED`

On the Issue Detail page, show a "Review Replacement Request" button. Clicking it opens a modal/dialog with:

*   **Decision** — radio buttons or dropdown: `APPROVE`, `REJECT` (required).
*   **Remarks** — textarea (optional, for approval notes).
*   **Rejection Reason** — textarea (required only when decision is `REJECT`).

On submit, call `PUT /assets/{asset_id}/issues/{timestamp}/management-review` with the `ManagementReviewIssueRequest` body.

On success:

*   If `APPROVE`: Show toast "Replacement approved." Status becomes `REPLACEMENT_APPROVED`.
*   If `REJECT`: Show toast "Replacement request rejected." Status becomes `REPLACEMENT_REJECTED`.
*   Refresh the detail view.

Handle errors:

*   400 (ValidationError): "Rejection reason is required" — decision is REJECT but no reason provided.
*   404: "Issue record not found"
*   409: "Issue is not in REPLACEMENT\_REQUIRED status"

> Note: When a replacement is approved, the backend emits an EventBridge event (`ReplacementApproved`) that can trigger the Phase 5 Return Process for the defective unit. This happens server-side — no frontend action needed.

---

### 11\. Pending Replacements Dashboard (Management only)

**Render condition:** `role === "management"`

Create a dedicated page or section accessible from the main navigation: "Pending Replacements".

Call `GET /issues/pending-replacements` with query params: `page`, `page_size`, `sort_order`.

**Table columns:**

| Column | Field | Notes |
| --- | --- | --- |
| Asset ID | `asset_id` | Link to asset detail |
| Issue Description | `issue_description` | Truncate if long |
| Action Path | `action_path` | Should always be "REPLACEMENT" |
| Replacement Justification | `replacement_justification` | Truncate if long |
| Reported By | `reported_by` | Employee who reported the issue |
| Triaged By | `triaged_by` | IT Admin who triaged |
| Resolved By | `resolved_by` | IT Admin who requested replacement |
| Created At | `created_at` | Formatted date |
| Actions | — | Link to issue detail |

Include pagination controls. Clicking a row navigates to the Issue Detail page (Feature 4) where Management can review it.

If no pending replacements exist, show: "No pending replacement requests."

---

## Conditional Rendering Summary

| Component / Action | it-admin | management | employee | finance |
| --- | --- | --- | --- | --- |
| "Report Issue" button (ASSIGNED assets, assigned employee) | ❌ | ❌ | ✅ (assigned only) | ❌ |
| "Upload Issue Photos" (after submission) | ❌ | ❌ | ✅ (assigned only) | ❌ |
| `/maintenance` page (Issues list with tabs) | ✅ | ❌ | ✅ (assigned only) | ❌ |
| Issue Detail view | ✅ | ✅ | ✅ (assigned only) | ❌ |
| "Triage Issue" button (ISSUE\_REPORTED) | ✅ | ❌ | ❌ | ❌ |
| "Start Repair" button (TROUBLESHOOTING) | ✅ | ❌ | ❌ | ❌ |
| "Send to Warranty" button (UNDER\_REPAIR) | ✅ | ❌ | ❌ | ❌ |
| "Complete Repair" button (UNDER\_REPAIR / SEND\_WARRANTY) | ✅ | ❌ | ❌ | ❌ |
| "Review Replacement Request" button (REPLACEMENT\_REQUIRED) | ❌ | ✅ | ❌ | ❌ |
| "Pending Replacements" page/nav item | ❌ | ✅ | ❌ | ❌ |

---

## Asset Detail Page — Conditional Action Buttons (Phase 4 additions)

On the Asset Detail page, render Phase 4 action buttons based on role AND asset/issue status:

```
if role === "employee":
    if asset status === "ASSIGNED" AND employee is the assigned user:
        → Show "Report Issue" button
        → Link to /maintenance page (scoped to their asset)

if role === "it-admin":
    → /maintenance page shows all issues across assets
    // Action buttons appear on the Issue Detail page, not the Asset Detail page.
    // The IT Admin navigates: /maintenance → Issue row → Issue Detail → action buttons.
```

> Management does not see the issues tab on the Asset Detail page. They access pending replacement requests through the dedicated "Pending Replacements" dashboard page.

---

## Status Badge Colors

Use consistent color coding for issue statuses:

| Status | Color | Label |
| --- | --- | --- |
| `ISSUE_REPORTED` | danger | Issue Reported |
| `TROUBLESHOOTING` | warning | Troubleshooting |
| `UNDER_REPAIR` | info | Under Repair |
| `SEND_WARRANTY` | info | Sent to Warranty |
| `RESOLVED` | success | Resolved |
| `REPLACEMENT_REQUIRED` | warning | Replacement Required |
| `REPLACEMENT_APPROVED` | success | Replacement Approved |
| `REPLACEMENT_REJECTED` | danger | Replacement Rejected |

---

## Error Response Format

The API returns errors in the shape: `{ "message": "..." }`. Always display the `message` field to the user for 4xx errors, as they contain contextual information (e.g. conflict reasons in 409 messages).

---

## Notes

*   The asset status changes as the issue progresses. When an issue is submitted, the asset moves from `ASSIGNED` to `ISSUE_REPORTED` and the issue record is created with status `TROUBLESHOOTING`. It transitions through `UNDER_REPAIR`, `SEND_WARRANTY`, or `REPLACEMENT_REQUIRED` as the IT Admin works through the issue. When a repair is completed, the asset reverts to `ASSIGNED`. This is different from Phase 3 (Software Requests) where the asset stays in `ASSIGNED` throughout.
*   The `action_path` field indicates which resolution path was taken: `"REPAIR"` or `"REPLACEMENT"`. Use this to conditionally show repair-specific or replacement-specific sections in the detail view.
*   The `timestamp` path parameter in URLs is the ISO-8601 timestamp from the `ISSUE#<Timestamp>` sort key. It uniquely identifies an issue within an asset.
*   All list endpoints support pagination with `page` and `page_size` query parameters. Default is page 1, 20 items per page.
*   The `status` filter on ListIssues uses exact matching against `IssueStatus` values.
*   There is no separate "My Issues" endpoint. Employees see their issues by viewing the Issues tab on their assigned asset's detail page.
*   The ListPendingReplacements endpoint only returns issues in `REPLACEMENT_REQUIRED` status. Once Management approves or rejects, the issue disappears from this list.
*   Issue evidence photos are uploaded directly to S3 via presigned PUT URLs, not through the API. The upload flow is: generate URLs → PUT files to S3. The photos then appear as `issue_photo_urls` (presigned GET URLs) in the Issue Detail response.
*   Presigned URLs for photo uploads expire after 15 minutes. Presigned GET URLs for viewing photos are generated fresh on each detail request. Handle expiry gracefully — if a fetch fails with 403 from S3, prompt the user to refresh.
*   SES email notifications are sent server-side on two events: (1) when an employee submits an issue (notifies IT Admins), and (2) when an IT Admin requests a replacement (notifies Management). No frontend action needed for either.
*   When Management approves a replacement, the backend emits an EventBridge event that can trigger the Phase 5 Return Process. This is a server-side integration — no frontend action needed.