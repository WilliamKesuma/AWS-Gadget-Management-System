# Frontend Implementation Prompt — Phase 6: Asset Disposal Process

## Context

You are building the React frontend for Phase 6 (Asset Disposal Process) of the Gadget Management System. The backend API is fully implemented. Every component and action described below must be conditionally rendered based on the user's role.

The disposal flow involves three actors:

*   **IT Admin** initiates the disposal request (provides reason and justification), and later completes the disposal (confirms data wipe and disposal date).
*   **Management** reviews the disposal request and approves or rejects it.
*   **Finance** is notified automatically (via email) when a disposal is completed, for asset write-off purposes. Finance has no interactive UI in this flow.

---

## API Endpoints

| Method | Path | Role(s) | Purpose |
| --- | --- | --- | --- |
| POST | `/assets/{asset_id}/disposals` | it-admin | Initiate a disposal request for an asset |
| PUT | `/assets/{asset_id}/disposals/{disposal_id}/management-review` | management | Approve or reject a disposal request |
| PUT | `/assets/{asset_id}/disposals/{disposal_id}/complete` | it-admin | Complete the disposal (data wipe + disposal date) |
| GET | `/assets/{asset_id}/disposals/{disposal_id}` | it-admin, management | View details of a specific disposal |
| GET | `/disposals` | it-admin | List all disposals (paginated, filterable) |
| GET | `/disposals/pending` | management | List pending disposal requests awaiting approval |

---

## TypeScript Types (already defined in `types.ts`)

```typescript
// Enums
type ApproveRejectDecision = "APPROVE" | "REJECT"
type AssetStatus =
    | "IN_STOCK" | "ASSIGNED" | "ASSET_PENDING_APPROVAL" | "ASSET_REJECTED"
    | "DISPOSAL_REVIEW" | "DISPOSAL_PENDING"
    | "DISPOSED" | "RETURN_PENDING" | "DAMAGED"
    | "UNDER_REPAIR" | "ISSUE_REPORTED"
type FinanceNotificationStatus = "QUEUED" | "COMPLETED" | "NO_FINANCE_USERS" | "FAILED"

type AssetSpecs = {
    brand?: string
    model?: string
    serial_number?: string
    product_description?: string
    cost?: number
    purchase_date?: string
}

// Initiate Disposal (IT Admin)
type InitiateDisposalRequest = {
    disposal_reason: string
    justification: string
}

type InitiateDisposalResponse = {
    asset_id: string
    disposal_id: string
    status: AssetStatus  // "DISPOSAL_PENDING"
}

// Management Review (Management)
type ManagementReviewDisposalRequest = {
    decision: ApproveRejectDecision
    remarks?: string
    rejection_reason?: string
}

type ManagementReviewDisposalResponse = {
    asset_id: string
    disposal_id: string
    status: AssetStatus  // "DISPOSAL_PENDING" (asset stays DISPOSAL_PENDING, ManagementApprovedAt signals approval) or "IN_STOCK" (rejection returns asset to stock)
}

// Complete Disposal (IT Admin)
type CompleteDisposalRequest = {
    disposal_date: string
    data_wipe_confirmed: boolean  // MUST be true to proceed
}

type CompleteDisposalResponse = {
    asset_id: string
    disposal_id: string
    status: AssetStatus  // "DISPOSED"
    finance_notification_status: FinanceNotificationStatus
}

// Get Disposal Details (IT Admin + Management)
type GetDisposalDetailsResponse = {
    asset_id: string
    disposal_id: string
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

// List Disposals (IT Admin)
type ListDisposalsFilter = PaginatedAPIFilter & {
    disposal_reason?: string
    date_from?: string
    date_to?: string
}

type DisposalListItem = {
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

type ListDisposalsResponse = PaginatedAPIResponse<DisposalListItem>

// List Pending Disposals (Management)
type ListPendingDisposalsFilter = PaginatedAPIFilter & {
    disposal_reason?: string
}

type PendingDisposalItem = {
    asset_id: string
    disposal_id: string
    disposal_reason: string
    justification: string
    asset_specs?: AssetSpecs
    initiated_by: string
    initiated_by_id: string
    initiated_at: string
}

type ListPendingDisposalsResponse = PaginatedAPIResponse<PendingDisposalItem>
```

---

## Disposal Flow Overview

```
IT Admin selects an eligible asset (DISPOSAL_REVIEW, IN_STOCK, or DAMAGED)
    │
    ▼  (Feature 1) POST /assets/{asset_id}/disposals
    Fills in: disposal_reason, justification
    → Asset status: DISPOSAL_PENDING
    → Disposal record created (asset specs auto-fetched from DDB)
    → Management notified via email (SES) + in-app notification
    │
    ▼  Management receives notification
    │
    ▼  (Feature 2) GET /disposals/pending  [Management]
    Management sees pending disposal requests in their dashboard
    │
    ▼  (Feature 3) GET /assets/{asset_id}/disposals/{disposal_id}  [Management]
    Management views disposal details (asset specs, reason, justification)
    │
    ▼  (Feature 4) PUT /assets/{asset_id}/disposals/{disposal_id}/management-review  [Management]
    │
    ├── APPROVE
    │   → Asset status stays DISPOSAL_PENDING (ManagementApprovedAt timestamp signals approval)
    │   → IT Admin notified via email (SES) + in-app notification
    │   │
    │   ▼  (Feature 5) PUT /assets/{asset_id}/disposals/{disposal_id}/complete  [IT Admin]
    │   IT Admin submits: disposal_date, data_wipe_confirmed (must be true)
    │   → Asset status: DISPOSED (immutable — no further actions allowed)
    │   → Finance notified via email (asset write-off subject)
    │   → FinanceNotifiedAt timestamp logged
    │
    └── REJECT
        → Asset status: IN_STOCK (returned to stock, employee unlinked)
        → Mandatory rejection_reason provided
```

---

## Features to Implement

### 1\. Initiate Disposal (IT Admin only)

**Render condition:** `role === "it-admin"` AND asset status is one of: `DISPOSAL_REVIEW`, `IN_STOCK`, `DAMAGED`

On the Asset Detail page, show an "Initiate Disposal" button.

Clicking it opens a modal/dialog with a form containing:

*   **Disposal Reason** — text input (required, cannot be blank)
*   **Justification** — textarea (required, cannot be blank)

The modal should also display a read-only summary of the asset's details (brand, model, serial number, cost, etc.) fetched from the asset record, so the IT Admin can confirm they are disposing of the correct asset.

> Note: Asset specs (brand, model, serial_number, product_description, cost, purchase_date) are auto-fetched from the asset record by the backend and stored on the disposal record. They are NOT form fields.

On submit, call `POST /assets/{asset_id}/disposals` with the `InitiateDisposalRequest` body.

On success:

*   Show a success toast: "Disposal request submitted. Awaiting management approval."
*   Close the modal and refresh the asset detail view. Asset status becomes `DISPOSAL_PENDING`.

Handle these error cases:

*   400 (ValidationError): Display the validation message.
*   404: "Asset not found"
*   409: "Asset is not in a valid status for disposal" — the asset is in a status that does not allow disposal initiation.

---

### 2\. Pending Disposals List (Management only)

**Render condition:** `role === "management"`

Create a dedicated page or section accessible from the main navigation: "Pending Disposals".

Call `GET /disposals/pending` with optional query params: `page`, `page_size`, `disposal_reason`, `sort_order`.

**Table columns:**

| Column | Field | Notes |
| --- | --- | --- |
| Asset ID | `asset_id` | Link to disposal detail |
| Brand / Model | `asset_specs.brand`, `asset_specs.model` | Combined display, show "N/A" if null |
| Serial Number | `asset_specs.serial_number` | Show "N/A" if null |
| Disposal Reason | `disposal_reason` | Truncate if long |
| Justification | `justification` | Truncate if long |
| Initiated By | `initiated_by` | Resolved user name |
| Initiated At | `initiated_at` | Formatted date |
| Actions | — | "Review" button |

Clicking "Review" navigates to the Disposal Detail page for that `asset_id` + `disposal_id`.

Include pagination controls and an optional filter for `disposal_reason`.

If no pending disposals exist, show: "No pending disposal requests."

---

### 3\. View Disposal Details (IT Admin + Management)

**Render condition:** `role === "it-admin"` OR `role === "management"`

Call `GET /assets/{asset_id}/disposals/{disposal_id}`.

**Display fields:**

| Section | Fields |
| --- | --- |
| Disposal Info | `disposal_reason`, `justification`, `initiated_by`, `initiated_at` (formatted date) |
| Asset Details | `asset_specs.brand`, `asset_specs.model`, `asset_specs.serial_number`, `asset_specs.product_description`, `asset_specs.cost` (formatted currency), `asset_specs.purchase_date` (formatted date). Show "N/A" for null fields. |
| Management Review | `management_reviewed_by`, `management_reviewed_at` (formatted date), `management_remarks`, `management_rejection_reason`. Show only when `management_reviewed_at` is present. If approved, also show `management_approved_at` (formatted date). |
| Completion | `disposal_date` (formatted date), `data_wipe_confirmed` (badge: "Confirmed" / "Not Confirmed"), `completed_by`, `completed_at` (formatted date). Show only when `completed_at` is present. |
| Finance Notification | `finance_notification_status` (badge), `finance_notified_at` (formatted date). Show only when `finance_notification_sent` is true. |
| Lock Status | `is_locked` — if true, show a prominent banner: "This asset has been disposed and is now locked. No further actions are allowed." |

**Conditional action buttons on the detail view:**

*   If `role === "management"` AND asset status is `DISPOSAL_PENDING` → Show "Approve" and "Reject" buttons (Feature 4)
*   If `role === "it-admin"` AND asset status is `DISPOSAL_PENDING` AND `management_approved_at` is present → Show "Complete Disposal" button (Feature 5)
*   If `is_locked === true` → Hide ALL action buttons

---

### 4\. Management Review — Approve or Reject (Management only)

**Render condition:** `role === "management"` AND asset status is `DISPOSAL_PENDING`

From the Disposal Detail page (Feature 3), Management can approve or reject the disposal.

#### Approve Flow

Clicking "Approve" opens a confirmation dialog with:

*   **Remarks** — textarea (optional, for any notes)

On confirm, call `PUT /assets/{asset_id}/disposals/{disposal_id}/management-review` with:

```typescript
const request: ManagementReviewDisposalRequest = {
    decision: "APPROVE",
    remarks: remarksValue || undefined
}
```

On success:

*   Show a success toast: "Disposal request approved."
*   Refresh the detail view. The `management_approved_at` field will now be populated, indicating approval.

#### Reject Flow

Clicking "Reject" opens a dialog with:

*   **Rejection Reason** — textarea (required, cannot be blank)

On confirm, call `PUT /assets/{asset_id}/disposals/{disposal_id}/management-review` with:

```typescript
const request: ManagementReviewDisposalRequest = {
    decision: "REJECT",
    rejection_reason: rejectionReasonValue
}
```

On success:

*   Show a success toast: "Disposal request rejected."
*   Refresh the detail view. Asset status becomes `IN_STOCK` (returned to stock).

Handle these error cases:

*   400 (ValidationError): Display the validation message (e.g., missing rejection_reason on REJECT).
*   404: "Asset not found" or "Disposal record not found"
*   409: "Disposal is not in DISPOSAL_PENDING status"

---

### 5\. Complete Disposal (IT Admin only)

**Render condition:** `role === "it-admin"` AND asset status is `DISPOSAL_PENDING` AND `management_approved_at` is present

From the Disposal Detail page (Feature 3), IT Admin can complete the disposal after management approval.

Clicking "Complete Disposal" opens a modal/dialog with:

*   **Disposal Date** — date picker (required, format: YYYY-MM-DD)
*   **Data Wipe Confirmed** — checkbox (required, must be checked to proceed)

Client-side validation: If `data_wipe_confirmed` is false (checkbox unchecked), disable the submit button and show an inline message: "You must confirm that the device data has been wiped before completing the disposal."

On submit, call `PUT /assets/{asset_id}/disposals/{disposal_id}/complete` with the `CompleteDisposalRequest` body.

On success:

*   Show a success toast: "Disposal completed. Asset is now disposed."
*   If `finance_notification_status === "COMPLETED"`, show an additional info message: "Finance team has been notified for asset write-off."
*   If `finance_notification_status === "NO_FINANCE_USERS"`, show a warning: "No finance users found. Finance notification could not be sent."
*   If `finance_notification_status === "FAILED"`, show a warning: "Finance notification failed. Please notify the finance team manually."
*   Close the modal and refresh the detail view. Asset status becomes `DISPOSED` and `is_locked` becomes `true`.

Handle these error cases:

*   400 "DataWipeConfirmed must be true to complete disposal" — checkbox was not checked (server-side validation).
*   400 (ValidationError): Display the validation message.
*   404: "Asset not found" or "Disposal record not found"
*   409: "Disposal has not been approved by management"

---

### 6\. List All Disposals (IT Admin only)

**Render condition:** `role === "it-admin"`

Create a dedicated page accessible from the main navigation: "Disposals".

Call `GET /disposals` with optional query params: `page`, `page_size`, `status`, `disposal_reason`, `date_from`, `date_to`, `sort_order`.

**Table columns:**

| Column | Field | Notes |
| --- | --- | --- |
| Asset ID | `asset_id` | Link to disposal detail |
| Disposal Reason | `disposal_reason` | Truncate if long |
| Justification | `justification` | Truncate if long |
| Initiated By | `initiated_by` | Resolved user name |
| Initiated At | `initiated_at` | Formatted date |
| Status | `status` | Colored badge |
| Reviewed By | `management_reviewed_by` | Show "—" if null |
| Reviewed At | `management_reviewed_at` | Formatted date, show "—" if null |
| Disposal Date | `disposal_date` | Formatted date, show "—" if null |
| Actions | — | Link to disposal detail |

Include pagination controls and filters for:

*   `status` — dropdown: `DISPOSAL_PENDING`, `DISPOSED` (or "All")
*   `disposal_reason` — text input
*   `date_from` / `date_to` — date pickers (YYYY-MM-DD format)

If no disposals exist, show: "No disposal records found."

---

### 7\. Immutability Enforcement (DISPOSED assets)

When an asset's status is `DISPOSED`, the following rules apply across the entire application:

*   Hide ALL action buttons on the Asset Detail page (no assign, return, issue, software request, disposal, etc.)
*   Show a prominent banner on the Asset Detail page: "This asset has been disposed and is locked. No further actions are permitted."
*   On the Disposal Detail page, if `is_locked === true`, hide all action buttons and show the lock banner.
*   In any list view, `DISPOSED` assets should display the status badge but no action buttons.
*   If a user navigates directly to an action URL for a `DISPOSED` asset, show a read-only view with the lock banner instead of the action form.

---

## Conditional Rendering Summary

| Component / Action | it-admin | management | employee | finance |
| --- | --- | --- | --- | --- |
| "Initiate Disposal" button (eligible asset) | ✅ | ❌ | ❌ | ❌ |
| Disposal Detail view | ✅ | ✅ | ❌ | ❌ |
| "Approve" / "Reject" buttons (DISPOSAL\_PENDING) | ❌ | ✅ | ❌ | ❌ |
| "Complete Disposal" button (DISPOSAL\_PENDING + management\_approved\_at) | ✅ | ❌ | ❌ | ❌ |
| "Disposals" list page/nav item | ✅ | ❌ | ❌ | ❌ |
| "Pending Disposals" page/nav item | ❌ | ✅ | ❌ | ❌ |

---

## Status Badge Colors

Use consistent color coding for asset statuses relevant to the disposal flow:

| Status | Color | Label |
| --- | --- | --- |
| `DISPOSAL_REVIEW` | warning | Disposal Review |
| `DISPOSAL_PENDING` | warning | Disposal Pending |
| `DISPOSED` | neutral/gray | Disposed |

For finance notification status badges:

| Status | Color | Label |
| --- | --- | --- |
| `QUEUED` | warning | Queued |
| `COMPLETED` | success | Completed |
| `NO_FINANCE_USERS` | warning | No Finance Users |
| `FAILED` | danger | Failed |

For data wipe confirmation badges:

| Value | Color | Label |
| --- | --- | --- |
| `true` | success | Data Wipe Confirmed |
| `false` / null | danger | Not Confirmed |

---

## Notes

*   The `data_wipe_confirmed` field is validated server-side: if `false` is submitted, the backend returns 400. Add client-side validation as well — disable the submit button and show an inline warning when the checkbox is unchecked.
*   Asset specs (brand, model, serial_number, product_description, cost, purchase_date) are auto-fetched from the asset record by the backend when the disposal is initiated. They are displayed on the Disposal Detail page and the Pending Disposals list but are NOT form fields.
*   The `management_approved_at` field is only populated when management approves the disposal. It is distinct from `management_reviewed_at`, which is set on both approve and reject. Use `management_approved_at` to display when the approval was granted.
*   When management rejects a disposal, `rejection_reason` is mandatory. The frontend should validate this before submission and show an inline error if blank.
*   The `is_locked` field on `GetDisposalDetailsResponse` indicates the asset is `DISPOSED` and immutable. Always check this field to determine whether to show action buttons.
*   Finance notification happens automatically on the backend when disposal is completed. The frontend only needs to display the `finance_notification_status` and `finance_notified_at` on the Disposal Detail page.
*   The `ListDisposals` endpoint supports filtering by `status` as a query parameter. When a status is provided, it queries the `DisposalStatusIndex` GSI. When no status is provided, it queries the `DisposalEntityIndex` GSI to return all disposals.
*   The `ListPendingDisposals` endpoint is restricted to `management` role and only returns disposals with `DISPOSAL_PENDING` status.
*   Disposal dates should be formatted consistently across the UI (e.g., "Mar 25, 2026" or your app's standard date format).
*   After a disposal is completed and the asset becomes `DISPOSED`, navigating back to the Asset Detail page should reflect the locked state immediately.