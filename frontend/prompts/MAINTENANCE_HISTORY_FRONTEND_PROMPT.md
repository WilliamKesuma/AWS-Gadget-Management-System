# Frontend Implementation Prompt — Maintenance History

## Context

You are building the React frontend for the Maintenance History feature of the Gadget Management System. The backend API is fully implemented. This feature provides a unified, read-only view of all maintenance-related activity across all assets — issues, software requests, returns, and disposals — in a single paginated list.

This is an **IT Admin-only** feature. No other roles have access.

---

## API Endpoints

| Method | Path | Role(s) | Purpose |
| --- | --- | --- | --- |
| GET | `/maintenance-history` | it-admin | List all maintenance history records (paginated, filterable) |

---

## TypeScript Types (already defined in `types.ts`)

```typescript
// Enum
type MaintenanceRecordType = "ISSUE" | "SOFTWARE_REQUEST" | "RETURN" | "DISPOSAL"
type SortOrder = "asc" | "desc"

// Filter
type ListMaintenanceHistoryFilter = PaginatedAPIFilter & {
    record_type?: MaintenanceRecordType
    sort_order?: SortOrder
}

// Response item
type MaintenanceHistoryItem = {
    asset_id: string
    record_id: string
    record_type: MaintenanceRecordType
    status: string
    summary: string
    created_by: string
    created_by_id: string
    created_at: string
}

// Response
type ListMaintenanceHistoryResponse = PaginatedAPIResponse<MaintenanceHistoryItem>
```

---

## Labels

Add the following to `labels.ts`:

```typescript
import type { MaintenanceRecordType } from "./types"

export const MaintenanceRecordTypeLabels: Record<MaintenanceRecordType, string> = {
    ISSUE: "Issue",
    SOFTWARE_REQUEST: "Software Request",
    RETURN: "Return",
    DISPOSAL: "Disposal",
}
```

---

## Features to Implement

### 1. Maintenance History List Page (IT Admin only)

**Render condition:** `role === "it-admin"`

Create a dedicated page accessible from the main navigation: "Maintenance History".

Call `GET /maintenance-history` with optional query params: `page`, `page_size`, `record_type`, `sort_order`.

**Table columns:**

| Column | Field | Notes |
| --- | --- | --- |
| Asset ID | `asset_id` | Link to asset detail page (`/assets/{asset_id}`) |
| Type | `record_type` | Colored badge using `MaintenanceRecordTypeLabels` |
| Summary | `summary` | Truncate to ~80 characters if long |
| Status | `status` | Colored badge (see status badge colors below) |
| Created By | `created_by` | Resolved user name (already resolved by backend) |
| Created At | `created_at` | Formatted date (e.g., "Mar 25, 2026 14:35") |
| Actions | — | "View" link navigating to the relevant detail page |

**"View" link routing logic:**

The "View" action should navigate to the appropriate detail page based on `record_type`:

| `record_type` | Navigation target |
| --- | --- |
| `ISSUE` | `/assets/{asset_id}/issues/{record_id}` |
| `SOFTWARE_REQUEST` | `/assets/{asset_id}/software-requests/{record_id}` |
| `RETURN` | `/assets/{asset_id}/returns/{record_id}` |
| `DISPOSAL` | `/assets/{asset_id}/disposals/{record_id}` |

**Filters:**

*   **Record Type** — dropdown: "All", "Issue", "Software Request", "Return", "Disposal". Maps to the `record_type` query parameter. "All" sends no `record_type` param.
*   **Sort Order** — dropdown: "Newest First" (desc, default), "Oldest First" (asc). Maps to the `sort_order` query parameter.

**Pagination:**

Include standard pagination controls (page number, page size selector) consistent with other list pages in the application.

**Empty state:**

If no records exist, show: "No maintenance history records found."

If no records match the current filter, show: "No records match the selected filter."

---

## Conditional Rendering Summary

| Component / Action | it-admin | management | employee | finance |
| --- | --- | --- | --- | --- |
| "Maintenance History" nav item | ✅ | ❌ | ❌ | ❌ |
| Maintenance History list page | ✅ | ❌ | ❌ | ❌ |

---

## Status Badge Colors

The `status` field contains the domain-specific status string for each record type. Use the following color mapping:

### Issue statuses

| Status | Color | Label |
| --- | --- | --- |
| `TROUBLESHOOTING` | info | Troubleshooting |
| `UNDER_REPAIR` | warning | Under Repair |
| `SEND_WARRANTY` | warning | Sent to Warranty |
| `RESOLVED` | success | Resolved |
| `REPLACEMENT_REQUIRED` | danger | Replacement Required |
| `REPLACEMENT_APPROVED` | success | Replacement Approved |
| `REPLACEMENT_REJECTED` | danger | Replacement Rejected |

### Software request statuses

| Status | Color | Label |
| --- | --- | --- |
| `PENDING_REVIEW` | info | Pending Review |
| `ESCALATED_TO_MANAGEMENT` | warning | Escalated to Management |
| `SOFTWARE_INSTALL_APPROVED` | success | Approved |
| `SOFTWARE_INSTALL_REJECTED` | danger | Rejected |

### Return statuses

| Status | Color | Label |
| --- | --- | --- |
| `RETURN_PENDING` | warning | Return Pending |
| `IN_STOCK` | success | Returned to Stock |
| `DAMAGED` | danger | Damaged |
| `DISPOSAL_REVIEW` | warning | Disposal Review |
| `ISSUE_REPORTED` | warning | Issue Reported |

### Disposal statuses

| Status | Color | Label |
| --- | --- | --- |
| `DISPOSAL_PENDING` | warning | Disposal Pending |
| `DISPOSAL_REJECTED` | danger | Disposal Rejected |
| `DISPOSED` | neutral/gray | Disposed |

### Record type badge colors

| Record Type | Color | Label |
| --- | --- | --- |
| `ISSUE` | danger | Issue |
| `SOFTWARE_REQUEST` | info | Software Request |
| `RETURN` | warning | Return |
| `DISPOSAL` | neutral/gray | Disposal |

---

## Notes

*   The `status` field is a plain string because it spans multiple enum domains (issue statuses, software statuses, return resolved statuses, disposal statuses). Use the `record_type` to determine which status label map to apply when rendering the badge.
*   The `summary` field contains contextual information depending on the record type: issue description for issues, software name for software requests, remarks for returns, and disposal reason for disposals.
*   The `created_by` field is already resolved to a human-readable name by the backend. Display it directly — no additional user lookup is needed.
*   The `created_at` field is an ISO-8601 UTC timestamp. Format it consistently with other dates in the application.
*   The `record_id` is the UUID of the specific sub-record (IssueID, SoftwareRequestID, ReturnID, or DisposalID). Combined with `asset_id` and `record_type`, it provides enough information to construct the navigation link to the detail page.
*   This is a read-only list view. There are no create, update, or delete actions on this page.
*   The default sort order is `desc` (newest first), which matches the most common use case of reviewing recent maintenance activity.
*   Pagination follows the same `PaginatedAPIResponse` pattern used by all other list endpoints in the application.
