# Design Document — Software Installation Governance (Phase 3)

## Overview

This document describes the technical design for the Software Installation Governance feature. The implementation adds a two-tier software request approval workflow to the existing Gadget Management System React frontend, integrating with the fully-implemented backend API. All new code follows the established patterns for routing (TanStack Router file-based), server state (TanStack Query with custom hooks), forms (TanStack Form + Zod), tables (TanStack Table via `DataTable`), and role-based access (`useCurrentUserRole` + `beforeLoad` guards).

---

## Architecture

### New Files

```
src/
  hooks/
    use-software-requests.ts          # All useQuery + useMutation hooks for software requests
  components/
    software/
      SubmitSoftwareRequestDialog.tsx  # Employee submit form dialog
      ITAdminReviewDialog.tsx          # IT Admin review form dialog
      ManagementReviewDialog.tsx       # Management review form dialog
      SoftwareRequestsTab.tsx          # Tab/section on Asset Detail page
      SoftwareRequestDetail.tsx        # Detail view component
      SoftwareStatusBadge.tsx          # Reusable status badge
      RiskLevelBadge.tsx               # Reusable risk/impact badge
    assets.$asset_id.software-requests.tsx        # Software requests tab route (nested)
    assets.$asset_id.software-requests.$timestamp.tsx  # Detail route (nested)
```

### Modified Files

```
src/lib/query-keys.ts                              # Add softwareRequests namespace
src/lib/models/labels.ts                           # Add SoftwareStatus + risk level labels
src/routes/_authenticated/requests/index.tsx       # Add escalated dashboard content for management role
src/routes/_authenticated/assets.$asset_id.tsx     # Add Software Requests tab + submit button
```

---

## Data Flow

### Query Keys (query-keys.ts additions)

```
softwareRequests: {
  all: () => ['software-requests'] as const,
  list: (assetId: string, params: ListSoftwareRequestsFilter) =>
    [...queryKeys.softwareRequests.all(), 'list', assetId, params] as const,
  detail: (assetId: string, timestamp: string) =>
    [...queryKeys.softwareRequests.all(), 'detail', assetId, timestamp] as const,
  escalated: (params: ListEscalatedRequestsFilter) =>
    [...queryKeys.softwareRequests.all(), 'escalated', params] as const,
}
```

### Custom Hooks (use-software-requests.ts)

*   `useSoftwareRequests(assetId, filters, page, pageSize)` — `useQuery` for list
*   `useSoftwareRequestDetail(assetId, timestamp)` — `useQuery` for detail
*   `useEscalatedRequests(filters, page, pageSize)` — `useQuery` for escalated list
*   `useSubmitSoftwareRequest(assetId)` — `useMutation` for POST
*   `useReviewSoftwareRequest(assetId, timestamp)` — `useMutation` for IT Admin PUT
*   `useManagementReviewSoftwareRequest(assetId, timestamp)` — `useMutation` for Management PUT

All mutations use `onSettled` to call `queryClient.invalidateQueries` with the factory keys.

---

## Route Structure

### Escalated Dashboard

*   **Path:** `/_authenticated/requests/`
*   **File:** `src/routes/_authenticated/requests/index.tsx` (existing stub — updated)
*   **Guard:** existing `beforeLoad` already allows `management`; no change needed
*   **Note:** Management already has "Requests" in their nav. No new nav item is added — the escalated dashboard is the content of this existing page for the `management` role.

### Software Requests Tab (nested under asset detail)

*   **Path:** `/_authenticated/assets/$asset_id/software-requests`
*   **File:** `src/routes/_authenticated/assets.$asset_id.software-requests.tsx`
*   **Guard:** `beforeLoad` — `it-admin` or `employee`; others redirect to `/unauthorized`
*   **Search params (Zod):** `page`, `page_size`, `status`, `risk_level`, `software_name`, `vendor`, `license_validity_period`, `data_access_impact`

### Software Request Detail (nested under asset detail)

*   **Path:** `/_authenticated/assets/$asset_id/software-requests/$timestamp`
*   **File:** `src/routes/_authenticated/assets.$asset_id.software-requests.$timestamp.tsx`
*   **Guard:** `beforeLoad` — `it-admin`, `management`, or `employee`; others redirect to `/unauthorized`

---

## Component Design

### SoftwareStatusBadge

Maps `SoftwareStatus` to a `Badge` variant:

| Status | Variant | Label |
| --- | --- | --- |
| `PENDING_REVIEW` | `info` | Pending Review |
| `ESCALATED_TO_MANAGEMENT` | `warning` | Escalated to Management |
| `SOFTWARE_INSTALL_APPROVED` | `success` | Approved |
| `SOFTWARE_INSTALL_REJECTED` | `danger` | Rejected |

### RiskLevelBadge

Maps `"LOW" | "MEDIUM" | "HIGH"` to a `Badge` variant (used for both `risk_level` and `data_access_impact`):

| Value | Variant |
| --- | --- |
| `LOW` | `success` |
| `MEDIUM` | `info` |
| `HIGH` | `danger` |

### SubmitSoftwareRequestDialog

*   Opens via "Request Software Installation" button on Asset Detail
*   TanStack Form + Zod schema with `onSubmit` validation
*   Fields: `software_name`, `version`, `vendor`, `justification` (textarea), `license_type`, `license_validity_period`, `data_access_impact` (Select)
*   On success: `toast.success(...)`, close dialog, invalidate list query
*   On 400: inline `alert-danger` with `err.message` inside the dialog
*   On 403/404/409: `toast.error(err.message)`
*   Submit button disabled while `isPending`
*   Scrollable content area uses `-mx-1 px-1` pattern; action buttons in `DialogFooter`

### ITAdminReviewDialog

*   Opens via "Review Request" button on Software Request Detail
*   Fields: `risk_level` (Select), `decision` (radio/Select), `rejection_reason` (textarea, conditional)
*   Decision options are dynamically constrained:
    *   `risk_level = LOW` → enable APPROVE, REJECT; disable ESCALATE
    *   `risk_level = MEDIUM | HIGH` → enable ESCALATE, REJECT; disable APPROVE
*   On success: `toast.success(...)` per decision, close dialog, invalidate detail query
*   On 400: inline `alert-danger` inside dialog
*   On 404/409: `toast.error(err.message)`

### ManagementReviewDialog

*   Opens via "Review Escalated Request" button on Software Request Detail
*   Fields: `decision` (radio/Select: APPROVE, REJECT), `remarks` (textarea, optional), `rejection_reason` (textarea, required when REJECT)
*   On success: `toast.success(...)` per decision, close dialog, invalidate detail query
*   On 400: inline `alert-danger` inside dialog
*   On 404/409: `toast.error(err.message)`

### SoftwareRequestsTab

*   Rendered on Asset Detail page for `it-admin` (any asset) and `employee` (assigned only)
*   Uses `DataTable` with `createColumnHelper<SoftwareRequestListItem>()`
*   Columns defined outside component with `useMemo` for data
*   Filter state synced to URL search params via `validateSearch` Zod schema
*   Filter dialog (Dialog pattern) with draft state; "Apply Filters" commits to URL
*   Toolbar: "Filters" button with active filter count badge + "Clear all" button
*   Empty state: custom `TableCell` message "No software installation requests for this asset."
*   Actions column: eye icon `<Link>` to detail route; no dropdown needed (view only)

### SoftwareRequestDetail

*   Displays all sections conditionally based on populated fields
*   Renders `SoftwareStatusBadge`, `RiskLevelBadge` for status/risk/impact
*   Uses `formatDate` for all date fields
*   Conditional buttons: "Review Request" (it-admin + PENDING\_REVIEW), "Review Escalated Request" (management + ESCALATED\_TO\_MANAGEMENT)
*   Inline `alert-danger` for query errors

### Escalated Dashboard (requests/index.tsx)

*   Replaces the stub content in the existing `requests/index.tsx` route
*   Renders the escalated software requests table for `management` role
*   Uses `DataTable` with `createColumnHelper<EscalatedRequestListItem>()`
*   Asset ID column renders as `<Link to="/assets/$asset_id">`
*   Filter dialog with only `risk_level` filter
*   Filter + pagination synced to URL search params
*   Empty state: "No escalated software requests pending review."
*   Actions column: eye icon `<Link>` to detail route

---

## Asset Detail Page Integration

The existing `assets.$asset_id.tsx` is modified to:

1.  Add a "Software Requests" tab/section that renders `<SoftwareRequestsTab>` when role is `it-admin` or (role is `employee` AND assigned user matches current user)
2.  Add a "Request Software Installation" button in `QuickActionsCard` or as a standalone button when role is `employee` AND asset status is `ASSIGNED` AND assigned user matches current user

The current user's `user_id` is obtained from `useCurrentUser()` and compared against `asset.assignee?.user_id`.

---

## Header Navigation Update

No changes to `Header.tsx` are required. Management already has a "Requests" nav item pointing to `/requests`, which will now render the escalated software dashboard.

---

## Labels (labels.ts additions)

```
export const SOFTWARE_STATUS_LABELS: Record<SoftwareStatus, string> = {
  PENDING_REVIEW: 'Pending Review',
  ESCALATED_TO_MANAGEMENT: 'Escalated to Management',
  SOFTWARE_INSTALL_APPROVED: 'Approved',
  SOFTWARE_INSTALL_REJECTED: 'Rejected',
}

export const RISK_LEVEL_LABELS: Record<'LOW' | 'MEDIUM' | 'HIGH', string> = {
  LOW: 'Low',
  MEDIUM: 'Medium',
  HIGH: 'High',
}
```

---

## Correctness Properties

### Property 1: Decision options are constrained by risk level (invariant)

For any rendered `ITAdminReviewDialog`, the set of enabled decision options must satisfy:

*   `risk_level === 'LOW'` → enabled decisions ⊆ `{ 'APPROVE', 'REJECT' }`, `'ESCALATE'` is disabled
*   `risk_level === 'MEDIUM' | 'HIGH'` → enabled decisions ⊆ `{ 'ESCALATE', 'REJECT' }`, `'APPROVE'` is disabled

This invariant must hold regardless of the order in which the user changes the risk level field.

### Property 2: Submit button visibility is a pure function of role + asset state (property)

Given any combination of `(role, assetStatus, isAssignedUser)`, the "Request Software Installation" button visibility is deterministic:

*   Visible iff `role === 'employee' AND assetStatus === 'ASSIGNED' AND isAssignedUser === true`
*   All other combinations → not visible

### Property 3: Cache invalidation after every mutation (invariant)

After any successful or failed mutation (submit, IT Admin review, management review), `queryClient.invalidateQueries` is called via `onSettled` with the relevant factory key. The detail and list queries for the affected asset must be invalidated — never stale after a mutation completes.

### Property 4: Filter state round-trips through URL search params (round-trip)

For any set of filter values applied via the filter dialog, serializing to URL search params and then parsing back via the Zod `validateSearch` schema must produce an equivalent filter object. `parse(serialize(filters)) ≡ filters` for all valid filter combinations.

### Property 5: Status badge variant is a total function (invariant)

`SoftwareStatusBadge` must handle all four `SoftwareStatus` values and produce a valid `Badge` variant. No status value may fall through to an undefined/default case.

### Property 6: Role-based tab visibility is exclusive (property)

The Software\_Requests\_Tab is never rendered for `management` or `finance` roles, regardless of asset state. The escalated dashboard content in `/requests` is only rendered for the `management` role — other roles visiting `/requests` see their own role-appropriate content.