# Frontend Implementation Prompt — Phase 3: Software Installation Governance

## Context

You are building the React frontend for Phase 3 (Software Installation Governance) of the Gadget Management System. The backend API is fully implemented. Users authenticate via Cognito and have one of these roles: `it-admin`, `management`, `employee`, `finance`. Every component and action described below must be conditionally rendered based on the user's role.

---

## API Endpoints

| Method | Path | Role(s) | Purpose |
| --- | --- | --- | --- |
| POST | `/assets/{asset_id}/software-requests` | employee | Submit a software installation request for an assigned asset |
| GET | `/assets/{asset_id}/software-requests` | it-admin, employee | List software installation requests for an asset (paginated, filterable) |
| GET | `/assets/{asset_id}/software-requests/{timestamp}` | it-admin, management, employee | View details of a specific software installation request |
| PUT | `/assets/{asset_id}/software-requests/{timestamp}/review` | it-admin | IT Admin reviews a request (approve/escalate/reject) with risk level |
| PUT | `/assets/{asset_id}/software-requests/{timestamp}/management-review` | management | Management reviews an escalated request (approve/reject) |
| GET | `/software-requests/escalated` | management | List all escalated software requests across all assets (paginated) |

---

## TypeScript Types (already defined in `types.ts`)

```
// Enums
type SoftwareStatus =
    | "PENDING_REVIEW"
    | "ESCALATED_TO_MANAGEMENT"
    | "SOFTWARE_INSTALL_APPROVED"
    | "SOFTWARE_INSTALL_REJECTED"

type DataAccessImpact = "LOW" | "MEDIUM" | "HIGH"

// Submit Software Request
type SubmitSoftwareRequestRequest = {
    software_name: string
    version: string
    vendor: string
    justification: string
    license_type: string
    license_validity_period: string
    data_access_impact: DataAccessImpact   // constrained to "LOW" | "MEDIUM" | "HIGH"
}

type SubmitSoftwareRequestResponse = {
    asset_id: string
    timestamp: string
    status: SoftwareStatus
}

// IT Admin Review
type ReviewSoftwareRequestRequest = {
    decision: "APPROVE" | "ESCALATE" | "REJECT"
    risk_level: "LOW" | "MEDIUM" | "HIGH"
    rejection_reason?: string
}

type ReviewSoftwareRequestResponse = {
    asset_id: string
    timestamp: string
    status: SoftwareStatus
    risk_level: "LOW" | "MEDIUM" | "HIGH"
}

// Management Review
type ManagementReviewSoftwareRequestRequest = {
    decision: "APPROVE" | "REJECT"
    rejection_reason?: string
    remarks?: string
}

type ManagementReviewSoftwareRequestResponse = {
    asset_id: string
    timestamp: string
    status: SoftwareStatus
}

// Get Software Request Detail
type GetSoftwareRequestResponse = {
    asset_id: string
    timestamp: string
    software_name: string
    version: string
    vendor: string
    justification: string
    license_type: string
    license_validity_period: string
    data_access_impact: string             // employee's initial self-assessment
    status: SoftwareStatus
    risk_level?: "LOW" | "MEDIUM" | "HIGH" // IT Admin's verified technical assessment
    requested_by: string
    reviewed_by?: string
    reviewed_at?: string
    rejection_reason?: string
    management_reviewed_by?: string
    management_reviewed_at?: string
    management_rejection_reason?: string
    management_remarks?: string
    created_at: string
    installation_timestamp?: string
}

// List Software Requests (per asset)
type ListSoftwareRequestsFilter = PaginatedAPIFilter & {
    status?: SoftwareStatus
    risk_level?: "LOW" | "MEDIUM" | "HIGH"
    software_name?: string
    vendor?: string
    license_validity_period?: string
    data_access_impact?: DataAccessImpact
}

type SoftwareRequestListItem = {
    asset_id: string
    timestamp: string
    software_name: string
    version: string
    vendor: string
    justification: string
    license_type: string
    license_validity_period: string
    data_access_impact: string
    status: SoftwareStatus
    risk_level?: "LOW" | "MEDIUM" | "HIGH"
    requested_by: string
    reviewed_by?: string
    rejection_reason?: string
    created_at: string
    reviewed_at?: string
}

type ListSoftwareRequestsResponse = PaginatedAPIResponse<SoftwareRequestListItem>

// List Escalated Requests (management dashboard)
type ListEscalatedRequestsFilter = PaginatedAPIFilter & {
    risk_level?: "LOW" | "MEDIUM" | "HIGH"
}

type EscalatedRequestListItem = {
    asset_id: string
    timestamp: string
    software_name: string
    version: string
    vendor: string
    justification: string
    license_type: string
    license_validity_period: string
    data_access_impact: string
    status: SoftwareStatus
    risk_level: "LOW" | "MEDIUM" | "HIGH"
    requested_by: string
    reviewed_by: string
    reviewed_at: string
    created_at: string
}

type ListEscalatedRequestsResponse = PaginatedAPIResponse<EscalatedRequestListItem>
```

---

## Two-Tier Impact Assessment Model

This system uses a two-tier impact model. Both values are stored independently and both are returned in API responses:

`**data_access_impact**` — The employee's self-assessed data access impact level, submitted with the request. Constrained to `"LOW"`, `"MEDIUM"`, or `"HIGH"`. This is the employee's initial perspective on how the software will access data.

`**risk_level**` — The IT Admin's verified technical assessment, assigned during review. Also `"LOW"`, `"MEDIUM"`, or `"HIGH"`. This drives the escalation logic:

*   `risk_level = "LOW"` → IT Admin can approve or reject directly
*   `risk_level = "MEDIUM"` or `"HIGH"` → IT Admin must escalate to Management (cannot approve directly)

Display both fields in the request detail view so reviewers can compare the employee's self-assessment against the IT Admin's technical assessment.

---

## Software Request Status Lifecycle

```
PENDING_REVIEW  →  SOFTWARE_INSTALL_APPROVED     (IT Admin approves LOW risk)
PENDING_REVIEW  →  SOFTWARE_INSTALL_REJECTED     (IT Admin rejects)
PENDING_REVIEW  →  ESCALATED_TO_MANAGEMENT       (IT Admin escalates MEDIUM/HIGH risk)
ESCALATED_TO_MANAGEMENT  →  SOFTWARE_INSTALL_APPROVED   (Management approves)
ESCALATED_TO_MANAGEMENT  →  SOFTWARE_INSTALL_REJECTED   (Management rejects)
```

The asset itself remains in `ASSIGNED` status throughout — the status lifecycle belongs to the software request record, not the asset.

---

## Features to Implement

### 1\. Submit Software Installation Request (Employee only)

**Render condition:** `role === "employee"` AND asset status is `ASSIGNED` AND the employee is the assigned user

On the Asset Detail page, show a "Request Software Installation" button.

Clicking it opens a modal/dialog with a form containing:

*   **Software Name** — text input (required)
*   **Version** — text input (required)
*   **Vendor** — text input (required)
*   **Justification** — textarea (required, explain why the software is needed)
*   **License Type** — text input (required, e.g. "Perpetual", "Subscription", "Open Source")
*   **License Validity Period** — text input (required, e.g. "1 Year", "Lifetime", "Monthly")
*   **Data Access Impact** — dropdown/select with options: `LOW`, `MEDIUM`, `HIGH` (required). This is the employee's self-assessment of how the software will access organizational data.

All fields are required. On submit, call `POST /assets/{asset_id}/software-requests` with the `SubmitSoftwareRequestRequest` body.

On success:

*   Show a success toast: "Software installation request submitted. IT Admin will review your request."
*   Close the modal and optionally refresh the software requests list for this asset.

Handle these error cases:

*   400 (ValidationError): Display the validation message. Common cases: empty fields, invalid `data_access_impact` value.
*   403: "You are not assigned to this asset" — the employee is not the assigned user.
*   404: "Asset not found" — the asset does not exist.
*   409: "Software installation requests are only allowed for assets in ASSIGNED status" — the asset is not in ASSIGNED status.

> Note: On successful submission, the backend also sends an email notification to all active IT Admin users via SES. This happens server-side — no frontend action needed.

---

### 2\. List Software Requests for an Asset (IT Admin + Employee)

**Render condition:** `role === "it-admin"` OR (`role === "employee"` AND the employee is the assigned user)

On the Asset Detail page, show a "Software Requests" tab or section.

Call `GET /assets/{asset_id}/software-requests` with query params: `page`, `page_size`, `sort_order`, and optional filters.

**Table columns:**

| Column | Field | Notes |
| --- | --- | --- |
| Software Name | `software_name` |   |
| Version | `version` |   |
| Vendor | `vendor` |   |
| Status | `status` | Render as a colored badge (see status badge colors below) |
| Risk Level | `risk_level` | Show "—" if not yet reviewed |
| Data Access Impact | `data_access_impact` | Employee's self-assessment |
| Requested By | `requested_by` | User ID — resolve to name if possible |
| Created At | `created_at` | Formatted date |
| Actions | — | Link/button to view detail |

**Filters (above the table):**

| Filter | Type | Query Param |
| --- | --- | --- |
| Status | Dropdown: `PENDING_REVIEW`, `ESCALATED_TO_MANAGEMENT`, `SOFTWARE_INSTALL_APPROVED`, `SOFTWARE_INSTALL_REJECTED` | `status` |
| Risk Level | Dropdown: `LOW`, `MEDIUM`, `HIGH` | `risk_level` |
| Software Name | Text input (case-insensitive contains match) | `software_name` |
| Vendor | Text input (case-insensitive contains match) | `vendor` |
| License Validity Period | Text input (case-insensitive contains match) | `license_validity_period` |
| Data Access Impact | Dropdown: `LOW`, `MEDIUM`, `HIGH` | `data_access_impact` |

All filters are optional and combine with AND logic. Include pagination controls.

Handle errors:

*   403: "Insufficient permissions" or "You are not assigned to this asset"
*   404: "Asset not found"

If no requests exist, show: "No software installation requests for this asset."

---

### 3\. View Software Request Detail (IT Admin + Management + Employee)

**Render condition:** `role === "it-admin"` OR `role === "management"` OR (`role === "employee"` AND the employee is the assigned user)

Clicking a row in the software requests list (or navigating directly) opens a detail view.

Call `GET /assets/{asset_id}/software-requests/{timestamp}`.

**Display fields:**

| Section | Fields |
| --- | --- |
| Request Info | `software_name`, `version`, `vendor`, `justification`, `license_type`, `license_validity_period` |
| Impact Assessment | `data_access_impact` (label: "Employee Assessment"), `risk_level` (label: "IT Admin Assessment" — show "Pending" if null) |
| Status | `status` (colored badge), `created_at`, `requested_by` |
| IT Admin Review | `reviewed_by`, `reviewed_at`, `rejection_reason` (if rejected) |
| Management Review | `management_reviewed_by`, `management_reviewed_at`, `management_rejection_reason` (if rejected), `management_remarks` |
| Installation | `installation_timestamp` (if approved — label: "Approved/Installed At") |

Show the IT Admin Review and Management Review sections only when those fields are populated.

**Conditional action buttons on the detail view:**

*   If `role === "it-admin"` AND `status === "PENDING_REVIEW"` → Show "Review Request" button (opens review form — see Feature 4)
*   If `role === "management"` AND `status === "ESCALATED_TO_MANAGEMENT"` → Show "Review Escalated Request" button (opens management review form — see Feature 5)

Handle errors:

*   403: "Insufficient permissions" or "You are not assigned to this asset"
*   404: "Asset not found" or "Software installation request not found"

---

### 4\. IT Admin Review (IT Admin only)

**Render condition:** `role === "it-admin"` AND request status is `PENDING_REVIEW`

On the Software Request Detail page, show a "Review Request" button. Clicking it opens a review modal/dialog with:

*   **Risk Level** — dropdown: `LOW`, `MEDIUM`, `HIGH` (required). This is the IT Admin's verified technical assessment.
*   **Decision** — radio buttons or dropdown: `APPROVE`, `ESCALATE`, `REJECT` (required).
    *   The available decisions are constrained by the selected risk level:
        *   `LOW` → `APPROVE` or `REJECT` (cannot escalate)
        *   `MEDIUM` → `ESCALATE` or `REJECT` (cannot approve directly)
        *   `HIGH` → `ESCALATE` or `REJECT` (cannot approve directly)
    *   Dynamically enable/disable decision options based on the selected risk level.
*   **Rejection Reason** — textarea (required only when decision is `REJECT`).

On submit, call `PUT /assets/{asset_id}/software-requests/{timestamp}/review` with the `ReviewSoftwareRequestRequest` body.

On success:

*   If `APPROVE`: Show toast "Software installation approved." Status becomes `SOFTWARE_INSTALL_APPROVED`.
*   If `ESCALATE`: Show toast "Request escalated to Management for review." Status becomes `ESCALATED_TO_MANAGEMENT`.
*   If `REJECT`: Show toast "Software installation request rejected." Status becomes `SOFTWARE_INSTALL_REJECTED`.
*   Refresh the detail view.

Handle these error cases:

*   400 (ValidationError): Display the validation message. Common cases:
    *   "MEDIUM and HIGH risk requests must be escalated to Management" — the IT Admin tried to approve a MEDIUM/HIGH risk request.
    *   "Low risk requests cannot be escalated; approve or reject directly" — the IT Admin tried to escalate a LOW risk request.
    *   "Rejection reason is required" — decision is REJECT but no reason provided.
*   404: "Software installation request not found"
*   409: "This request is not in a reviewable state" — the request has already been reviewed.

---

### 5\. Management Review of Escalated Request (Management only)

**Render condition:** `role === "management"` AND request status is `ESCALATED_TO_MANAGEMENT`

On the Software Request Detail page, show a "Review Escalated Request" button. Clicking it opens a review modal/dialog with:

*   **Decision** — radio buttons or dropdown: `APPROVE`, `REJECT` (required).
*   **Remarks** — textarea (optional, for approval notes).
*   **Rejection Reason** — textarea (required only when decision is `REJECT`).

On submit, call `PUT /assets/{asset_id}/software-requests/{timestamp}/management-review` with the `ManagementReviewSoftwareRequestRequest` body.

On success:

*   If `APPROVE`: Show toast "Software installation approved by Management." Status becomes `SOFTWARE_INSTALL_APPROVED`.
*   If `REJECT`: Show toast "Software installation request rejected by Management." Status becomes `SOFTWARE_INSTALL_REJECTED`.
*   Refresh the detail view.

Handle these error cases:

*   400 (ValidationError): "Rejection reason is required" — decision is REJECT but no reason provided.
*   404: "Software installation request not found"
*   409: "This request is not in a state that allows management review" — the request is not in ESCALATED\_TO\_MANAGEMENT status.

---

### 6\. Escalated Requests Dashboard (Management only)

**Render condition:** `role === "management"`

Create a dedicated page or section accessible from the main navigation: "Escalated Software Requests".

Call `GET /software-requests/escalated` with query params: `page`, `page_size`, `sort_order`, and optional `risk_level` filter.

**Table columns:**

| Column | Field | Notes |
| --- | --- | --- |
| Asset ID | `asset_id` | Link to asset detail |
| Software Name | `software_name` |   |
| Version | `version` |   |
| Vendor | `vendor` |   |
| Risk Level | `risk_level` | Colored badge |
| Data Access Impact | `data_access_impact` | Employee's self-assessment |
| Requested By | `requested_by` |   |
| Reviewed By | `reviewed_by` | IT Admin who escalated |
| Created At | `created_at` | Formatted date |
| Actions | — | Link to request detail |

**Filters:**

| Filter | Type | Query Param |
| --- | --- | --- |
| Risk Level | Dropdown: `LOW`, `MEDIUM`, `HIGH` | `risk_level` |

Include pagination controls. Clicking a row navigates to the Software Request Detail page (Feature 3) where the Management can review it.

If no escalated requests exist, show: "No escalated software requests pending review."

---

## Conditional Rendering Summary

| Component / Action | it-admin | management | employee | finance |
| --- | --- | --- | --- | --- |
| "Request Software Installation" button (ASSIGNED assets, assigned employee) | ❌ | ❌ | ✅ (assigned only) | ❌ |
| "Software Requests" tab on Asset Detail | ✅ | ❌ | ✅ (assigned only) | ❌ |
| Software Request Detail view | ✅ | ✅ | ✅ (assigned only) | ❌ |
| "Review Request" button (PENDING\_REVIEW) | ✅ | ❌ | ❌ | ❌ |
| "Review Escalated Request" button (ESCALATED\_TO\_MANAGEMENT) | ❌ | ✅ | ❌ | ❌ |
| "Escalated Software Requests" page/nav item | ❌ | ✅ | ❌ | ❌ |

---

## Asset Detail Page — Conditional Action Buttons (Phase 3 additions)

On the Asset Detail page, render Phase 3 action buttons based on role AND asset status:

```
if role === "employee":
    if status === "ASSIGNED" AND employee is the assigned user:
        → Show "Request Software Installation" button
        → Show "Software Requests" tab/section

if role === "it-admin":
    → Show "Software Requests" tab/section (for any asset)
```

> Management does not see the software requests tab on the Asset Detail page. They access escalated requests through the dedicated "Escalated Software Requests" dashboard page.

---

## Status Badge Colors

Use consistent color coding for software request statuses:

| Status | Color | Label |
| --- | --- | --- |
| `PENDING_REVIEW` | Info | Pending Review |
| `ESCALATED_TO_MANAGEMENT` | Warning | Escalated to Management |
| `SOFTWARE_INSTALL_APPROVED` | Success | Approved |
| `SOFTWARE_INSTALL_REJECTED` | Danger | Rejected |

For risk level badges:

| Risk Level | Color |
| --- | --- |
| `LOW` | Success |
| `MEDIUM` | Info |
| `HIGH` | Danger |

For data access impact badges (same color scheme as risk level):

| Impact | Color |
| --- | --- |
| `LOW` | Success |
| `MEDIUM` | Info |
| `HIGH` | Danger |

---

## Error Response Format

The API returns errors in the shape: `{ "message": "..." }`. Always display the `message` field to the user for 4xx errors, as they contain contextual information (e.g. conflict reasons in 409 messages).

---

## Notes

*   The asset status remains `ASSIGNED` throughout the software request lifecycle. The status field on the software request record tracks the governance workflow, not the asset itself.
*   The employee receives no email notification about the outcome of their request — they check the status via the list/detail views. IT Admins receive an email notification (via SES) when a new request is submitted. This happens server-side — no frontend action needed.
*   The IT Admin's `risk_level` drives the escalation logic. The employee's `data_access_impact` is informational metadata preserved for audit purposes. Both are displayed in the detail view.
*   The `decision` options in the IT Admin review form are constrained by `risk_level`: LOW can only be approved/rejected, MEDIUM/HIGH must be escalated or rejected. Enforce this in the UI by dynamically enabling/disabling options.
*   The `timestamp` path parameter in URLs is the ISO-8601 timestamp from the `SOFTWARE#<Timestamp>` sort key. It uniquely identifies a software request within an asset.
*   All list endpoints support pagination with `page` and `page_size` query parameters. Default is page 1, 20 items per page.
*   The `software_name`, `vendor`, and `license_validity_period` filters on ListSoftwareRequests use case-insensitive substring matching (contains). The `status`, `risk_level`, and `data_access_impact` filters use exact matching.
*   There is no separate "My Software Requests" endpoint. Employees see their requests by viewing the Software Requests tab on their assigned asset's detail page.
*   The ListEscalatedRequests endpoint only returns requests in `ESCALATED_TO_MANAGEMENT` status. Once Management approves or rejects, the request disappears from this list.