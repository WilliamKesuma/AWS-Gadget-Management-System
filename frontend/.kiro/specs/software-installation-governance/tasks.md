# Implementation Plan: Software Installation Governance

## Overview

Incrementally build the two-tier software request approval workflow into the existing React frontend. Each task builds on the previous, starting with shared infrastructure (types, query keys, labels, hooks), then badge components, then the main feature surfaces (tab, detail, dialogs, escalated dashboard), and finally wiring everything into the asset detail page and requests route.

## Tasks

1.  Add query keys, labels, and custom hooks

 1.1 Add `softwareRequests` namespace to `src/lib/query-keys.ts`

*   Add `all`, `list(assetId, params)`, `detail(assetId, timestamp)`, and `escalated(params)` factory keys
*   _Requirements: 8.1_

 1.2 Add software status and risk level labels to `src/lib/models/labels.ts`

*   Add `SOFTWARE_STATUS_LABELS` record mapping all four `SoftwareStatus` values
*   Add `RISK_LEVEL_LABELS` record mapping LOW, MEDIUM, HIGH
*   _Requirements: 2.5, 2.6, 2.7_

 1.3 Create `src/hooks/use-software-requests.ts` with all query and mutation hooks

*   `useSoftwareRequests(assetId, filters, page, pageSize)` — `useQuery` for `GET /assets/{asset_id}/software-requests`
*   `useSoftwareRequestDetail(assetId, timestamp)` — `useQuery` for `GET /assets/{asset_id}/software-requests/{timestamp}`
*   `useEscalatedRequests(filters, page, pageSize)` — `useQuery` for `GET /software-requests/escalated`
*   `useSubmitSoftwareRequest(assetId)` — `useMutation` for `POST /assets/{asset_id}/software-requests`, invalidates list query via `onSettled`
*   `useReviewSoftwareRequest(assetId, timestamp)` — `useMutation` for `PUT /assets/{asset_id}/software-requests/{timestamp}/review`, invalidates detail + list queries via `onSettled`
*   `useManagementReviewSoftwareRequest(assetId, timestamp)` — `useMutation` for `PUT /assets/{asset_id}/software-requests/{timestamp}/management-review`, invalidates detail + escalated queries via `onSettled`
*   All list/detail queries must have a non-zero `staleTime`
*   All mutations must use `mutationKey` for observability
*   _Requirements: 8.2, 8.3, 8.4, 1.4, 1.6, 4.5, 4.9, 5.3, 5.6_

1.  Checkpoint

*   Ensure all hooks compile without errors, ask the user if questions arise.

1.  Create badge components

 3.1 Create `src/components/software/SoftwareStatusBadge.tsx`

*   Map all four `SoftwareStatus` values to Badge variants: PENDING\_REVIEW → info, ESCALATED\_TO\_MANAGEMENT → warning, SOFTWARE\_INSTALL\_APPROVED → success, SOFTWARE\_INSTALL\_REJECTED → danger
*   Use `SOFTWARE_STATUS_LABELS` for display text
*   _Requirements: 2.5_

\[ \]\* 3.2 Write unit test for `SoftwareStatusBadge`

*   Verify all four status values produce the correct variant and label
*   **Property 5: Status badge variant is a total function**
*   **Validates: Requirements 2.5**

 3.3 Create `src/components/software/RiskLevelBadge.tsx`

*   Map LOW → success, MEDIUM → info, HIGH → danger
*   Use `RISK_LEVEL_LABELS` for display text
*   Accept a `value` prop of `"LOW" | "MEDIUM" | "HIGH" | null | undefined`; render "—" when null/undefined
*   Reuse for both `risk_level` and `data_access_impact` display
*   _Requirements: 2.6, 2.7_

1.  Create the SubmitSoftwareRequestDialog component

*   4.1 Create `src/components/software/SubmitSoftwareRequestDialog.tsx`
    *   TanStack Form + Zod schema with `onSubmit` validation
    *   Fields: software\_name, version, vendor, justification (textarea), license\_type, license\_validity\_period, data\_access\_impact (Select: LOW, MEDIUM, HIGH)
    *   All fields required per Zod schema
    *   Use `useSubmitSoftwareRequest` mutation
    *   On success: `toast.success("Software installation request submitted. IT Admin will review your request.")`, close dialog
    *   On 400: inline `alert-danger` with `err.message` inside dialog
    *   On 403/404/409: `toast.error(err.message)`
    *   Submit button disabled while `isPending`
    *   Scrollable content with `-mx-1 px-1` pattern; action buttons in `DialogFooter`
    *   _Requirements: 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11_

1.  Create the ITAdminReviewDialog component

 5.1 Create `src/components/software/ITAdminReviewDialog.tsx`

*   TanStack Form + Zod schema with `onSubmit` validation
*   Fields: risk\_level (Select: LOW, MEDIUM, HIGH), decision (Select: APPROVE, ESCALATE, REJECT), rejection\_reason (textarea, required only when REJECT)
*   Decision options dynamically constrained by risk\_level:
    *   LOW → APPROVE and REJECT enabled, ESCALATE disabled
    *   MEDIUM or HIGH → ESCALATE and REJECT enabled, APPROVE disabled
*   When risk\_level changes, reset decision if the current selection becomes invalid
*   Use `useReviewSoftwareRequest` mutation
*   On success: toast per decision ("Software installation approved." / "Request escalated to Management for review." / "Software installation request rejected."), close dialog
*   On 400: inline `alert-danger` inside dialog
*   On 404/409: `toast.error(err.message)`
*   Submit button disabled while `isPending`
*   _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11, 4.12, 4.13_

\[ \]\* 5.2 Write property test for ITAdminReviewDialog decision constraints

*   **Property 1: Decision options are constrained by risk level**
*   **Validates: Requirements 4.3, 4.4**

1.  Create the ManagementReviewDialog component

*   6.1 Create `src/components/software/ManagementReviewDialog.tsx`
    *   TanStack Form + Zod schema with `onSubmit` validation
    *   Fields: decision (Select: APPROVE, REJECT), remarks (textarea, optional), rejection\_reason (textarea, required only when REJECT)
    *   Use `useManagementReviewSoftwareRequest` mutation
    *   On success: toast per decision ("Software installation approved by Management." / "Software installation request rejected by Management."), close dialog
    *   On 400: inline `alert-danger` inside dialog
    *   On 404/409: `toast.error(err.message)`
    *   Submit button disabled while `isPending`
    *   _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10_

1.  Checkpoint

*   Ensure all dialog components compile without errors, ask the user if questions arise.

1.  Create the SoftwareRequestsTab component

 8.1 Create `src/components/software/SoftwareRequestsTab.tsx`

*   Use `DataTable` with `createColumnHelper<SoftwareRequestListItem>()`
*   Columns: Software Name, Version, Vendor, Status (SoftwareStatusBadge), Risk Level (RiskLevelBadge, "—" if null), Data Access Impact (RiskLevelBadge), Requested By, Created At (formatDate), Actions
*   Actions column: eye icon `<Link>` to software request detail route; no dropdown (view only)
*   Column definitions extracted outside component; data memoized with `useMemo`
*   Filter dialog (Dialog pattern) with draft state containing: Status (select), Risk Level (select), Software Name (text), Vendor (text), License Validity Period (text), Data Access Impact (select)
*   Toolbar: "Filters" button with active filter count badge + "Clear all" button
*   Filter state synced to URL search params; page resets to 1 on filter apply
*   Pagination via `page` and `page_size` search params
*   Empty state: "No software installation requests for this asset."
*   Inline error display for 403/404 query errors
*   _Requirements: 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12, 2.13, 2.14_

\[ \]\* 8.2 Write property test for filter URL round-trip

*   **Property 4: Filter state round-trips through URL search params**
*   **Validates: Requirements 2.9**

1.  Create the SoftwareRequestDetail component

 9.1 Create `src/components/software/SoftwareRequestDetail.tsx`

*   Sections: Request Info (software\_name, version, vendor, justification, license\_type, license\_validity\_period), Impact Assessment (data\_access\_impact as "Employee Assessment", risk\_level as "IT Admin Assessment" showing "Pending" if null), Status (SoftwareStatusBadge, created\_at via formatDate, requested\_by), IT Admin Review (reviewed\_by, reviewed\_at — only when reviewed\_by populated), Management Review (management\_reviewed\_by, management\_reviewed\_at, management\_rejection\_reason, management\_remarks — only when management\_reviewed\_by populated), Installation (installation\_timestamp as "Approved/Installed At" — only when populated)
*   Conditional "Review Request" button: visible when role is `it-admin` AND status is `PENDING_REVIEW`; opens ITAdminReviewDialog
*   Conditional "Review Escalated Request" button: visible when role is `management` AND status is `ESCALATED_TO_MANAGEMENT`; opens ManagementReviewDialog
*   Inline `alert-danger` for query errors (403/404)
*   Use `formatDate` for all date fields
*   _Requirements: 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11_

\[ \]\* 9.2 Write property test for submit button visibility

*   **Property 2: Submit button visibility is a pure function of role + asset state**
*   **Validates: Requirements 1.1, 7.3**

1.  Create route files

 10.1 Create `src/routes/_authenticated/assets.$asset_id.software-requests.tsx`

*   `beforeLoad` guard: allow `it-admin` and `employee`; redirect others to `/unauthorized`
*   `validateSearch` with Zod schema for: page, page\_size, status, risk\_level, software\_name, vendor, license\_validity\_period, data\_access\_impact
*   Render `SoftwareRequestsTab` component, passing `asset_id` from params
*   SEO: define `SOFTWARE_REQUESTS_SEO` const, apply `noindex, nofollow` robots override
*   _Requirements: 2.1, 2.2, 7.4_

 10.2 Create `src/routes/_authenticated/assets.$asset_id.software-requests.$timestamp.tsx`

*   `beforeLoad` guard: allow `it-admin`, `management`, `employee`; redirect others to `/unauthorized`
*   Render `SoftwareRequestDetail` component, passing `asset_id` and `timestamp` from params
*   SEO: define `SOFTWARE_REQUEST_DETAIL_SEO` const, apply `noindex, nofollow` robots override
*   _Requirements: 3.1, 3.2, 3.3, 7.2_

1.  Checkpoint

*   Ensure all new route files and components compile without errors, ask the user if questions arise.

1.  Integrate into asset detail page and requests route

 12.1 Modify `src/routes/_authenticated/assets.$asset_id.tsx`

*   Add "Software Requests" tab/link that navigates to the software-requests child route
*   Show tab when role is `it-admin` (any asset) OR role is `employee` AND `asset.assignee?.user_id` matches current user
*   Add "Request Software Installation" button visible only when role is `employee` AND asset status is `ASSIGNED` AND `asset.assignee?.user_id` matches current user
*   Wire button to open `SubmitSoftwareRequestDialog`
*   _Requirements: 1.1, 2.1, 2.2, 7.3, 7.4_

 12.2 Modify `src/routes/_authenticated/requests/index.tsx` for escalated dashboard

*   For `management` role: render escalated software requests table using `useEscalatedRequests`
*   Use `DataTable` with `createColumnHelper<EscalatedRequestListItem>()`
*   Columns: Asset ID (Link to asset detail), Software Name, Version, Vendor, Risk Level (RiskLevelBadge), Data Access Impact (RiskLevelBadge), Requested By, Reviewed By, Created At (formatDate), Actions (eye icon Link to detail route)
*   Filter dialog with Risk Level filter only
*   Filter + pagination synced to URL search params via `validateSearch` Zod schema
*   Empty state: "No escalated software requests pending review."
*   Inline error for 403 query errors
*   For `employee` and `it-admin` roles: keep existing "My Requests" content
*   _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 6.11, 7.1_

\[ \]\* 12.3 Write property test for role-based tab visibility

*   **Property 6: Role-based tab visibility is exclusive**
*   **Validates: Requirements 2.1, 2.2, 7.4**

1.  Final checkpoint

*   Ensure all tests pass and all components integrate correctly, ask the user if questions arise.

## Notes

*   Tasks marked with `*` are optional and can be skipped for faster MVP
*   Each task references specific requirements for traceability
*   Checkpoints ensure incremental validation
*   Property tests validate universal correctness properties from the design document
*   All steering rules apply: filter-ui (dialog pattern), error-feedback (toast for actions, inline for forms/queries), formatting (formatDate/formatNumber), table-actions (eye icon + dropdown), role-based-access, tanstack-form, tanstack-query, tanstack-router, tanstack-table, shadcn, seo