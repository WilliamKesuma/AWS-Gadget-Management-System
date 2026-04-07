# Implementation Plan: Issue Management

## Overview

Implement the full issue lifecycle workflow across three new/rewritten routes, a custom hook, query key extensions, shared components, and action dialogs. Tasks are ordered so each step builds on the previous, ending with full integration.

## Tasks

- [x] 1. Extend query key factory and add issue status labels
  - [x] 1.1 Add `issues` namespace to `src/lib/query-keys.ts`
    - Add `issues.all()`, `issues.list(assetId, filters)`, `issues.detail(assetId, timestamp)`, and `issues.pendingReplacements(filters)` following the existing factory pattern
    - Import `ListIssuesFilter` and `ListPendingReplacementsFilter` from `#/lib/models/new/types`
    - _Requirements: 14.1_

  - [ ]* 1.2 Write property test for query key factory uniqueness and stability
    - **Property 14: Query key factory produces unique, stable keys**
    - **Validates: Requirements 14.1**

  - [x] 1.3 Add `ISSUE_STATUS_LABELS` to `src/lib/models/labels.ts`
    - Export `ISSUE_STATUS_LABELS: Record<IssueStatus, string>` mapping all eight `IssueStatus` values to their display strings
    - Use `PENDING_APPROVAL` (not `REPLACEMENT_REQUIRED`) as the key, with label `"Pending Approval"`
    - _Requirements: 13.1–13.8_

- [x] 2. Create `IssueStatusBadge` component
  - [x] 2.1 Implement `src/components/issues/IssueStatusBadge.tsx`
    - Map each `IssueStatus` to a `Badge` variant (`danger`, `warning`, `info`, `success`) and label from `ISSUE_STATUS_LABELS`
    - `ISSUE_REPORTED` → `danger`, `TROUBLESHOOTING` → `warning`, `UNDER_REPAIR` → `info`, `SEND_WARRANTY` → `info`, `RESOLVED` → `success`, `PENDING_APPROVAL` → `warning`, `REPLACEMENT_APPROVED` → `success`, `REPLACEMENT_REJECTED` → `danger`
    - _Requirements: 13.1–13.8_

  - [ ]* 2.2 Write property test for `IssueStatusBadge` label coverage
    - **Property 13: Issue status badge covers all statuses**
    - **Validates: Requirements 13.1–13.8**

- [x] 3. Implement `src/hooks/use-issues.ts`
  - [x] 3.1 Implement query hooks: `useIssues`, `useIssueDetail`, `usePendingReplacements`
    - `useIssues(assetId, filters, page, pageSize?)` — `GET /assets/{assetId}/issues`, `staleTime: 60_000`
    - `useIssueDetail(assetId, timestamp)` — `GET /assets/{assetId}/issues/{timestamp}`, `staleTime: 5 * 60_000`
    - `usePendingReplacements(page, pageSize?)` — `GET /issues/pending-replacements`, `staleTime: 60_000`
    - All query keys must use `queryKeys.issues.*` factory
    - _Requirements: 14.2, 14.3_

  - [x] 3.2 Implement mutation hooks: `useSubmitIssue`, `useGenerateIssueUploadUrls`
    - `useSubmitIssue(assetId)` — `POST /assets/{assetId}/issues`, invalidates `queryKeys.issues.list(assetId, {})`
    - `useGenerateIssueUploadUrls(assetId, timestamp)` — `POST /assets/{assetId}/issues/{timestamp}/upload-urls`
    - Each mutation must have a `mutationKey` and `onSettled` with `queryClient.invalidateQueries`
    - _Requirements: 1.3, 2.2, 14.4, 14.5_

  - [x] 3.3 Implement mutation hooks: `useResolveRepair`, `useSendWarranty`, `useCompleteRepair`, `useRequestReplacement`, `useManagementReviewIssue`
    - `useResolveRepair(assetId, timestamp)` — `PUT /assets/{assetId}/issues/{timestamp}/resolve-repair`, invalidates detail + list
    - `useSendWarranty(assetId, timestamp)` — `PUT /assets/{assetId}/issues/{timestamp}/send-warranty`, invalidates detail + list
    - `useCompleteRepair(assetId, timestamp)` — `PUT /assets/{assetId}/issues/{timestamp}/complete-repair`, invalidates detail + list + `queryKeys.assets.detail(assetId)`
    - `useRequestReplacement(assetId, timestamp)` — `PUT /assets/{assetId}/issues/{timestamp}/request-replacement`, invalidates detail + list
    - `useManagementReviewIssue(assetId, timestamp)` — `PUT /assets/{assetId}/issues/{timestamp}/management-review`, invalidates detail + `queryKeys.issues.pendingReplacements({})`
    - Each mutation must have a `mutationKey` and `onSettled`
    - _Requirements: 7.2, 8.2, 9.2, 10.3, 11.2–11.3, 14.4, 14.5_

- [x] 4. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement `SubmitIssueDialog` and `UploadIssuePhotosDialog`
  - [x] 5.1 Implement `src/components/issues/SubmitIssueDialog.tsx`
    - TanStack Form with Zod schema: `issue_description` required (non-empty, non-whitespace-only)
    - Use `<Field>`, `<FieldLabel>`, `<FieldError>` from `#/components/ui/field`; `<Textarea>` for the field
    - On 400 error display inline `<FieldError>`; on 403/409 display `toast.error(err.message)`
    - On success: `toast.success("Issue reported successfully. IT Admin has been notified.")`, close dialog, call `onSuccess(timestamp)` callback
    - Disable submit button and show loading indicator while `isPending`
    - Action buttons in `<DialogFooter>`; scrollable content uses `-mx-1 px-1`
    - _Requirements: 1.2–1.8_

  - [ ]* 5.2 Write property test for whitespace-only description rejection
    - **Property 2: Whitespace-only descriptions are rejected**
    - **Validates: Requirements 1.3**

  - [ ]* 5.3 Write property test for submit button disabled while pending
    - **Property 3: Submit button is disabled while pending**
    - **Validates: Requirements 1.8_

  - [x] 5.4 Implement `src/components/issues/UploadIssuePhotosDialog.tsx`
    - Drag-and-drop zone accepting only `image/jpeg` and `image/png`; reject other types with inline validation message
    - On file selection call `useGenerateIssueUploadUrls` then `PUT` each file to S3 with `Content-Type` header
    - On all uploads success: `toast.success("Photos uploaded successfully.")`
    - On any S3 PUT failure: `toast.error("One or more photo uploads failed. Please try again.")`
    - On 400 from URL generation: display error `message` inline
    - Reuse `DragDropZone` from `src/components/assets/DragDropZone.tsx` if compatible
    - _Requirements: 2.1–2.7_

  - [ ]* 5.5 Write property test for non-image file rejection
    - **Property 4: Non-image files are rejected by the upload zone**
    - **Validates: Requirements 2.7**

- [x] 6. Implement IT Admin action dialogs
  - [x] 6.1 Implement `src/components/issues/StartRepairDialog.tsx`
    - TanStack Form with optional `repair_notes` textarea
    - On success: `toast.success("Repair initiated. Status updated to Under Repair.")`, close dialog, invalidate issue detail
    - On 404/409: `toast.error(err.message)`; disable submit while pending
    - _Requirements: 7.1–7.6_

  - [x] 6.2 Implement `src/components/issues/SendWarrantyDialog.tsx`
    - TanStack Form with optional `warranty_notes` textarea
    - On success: `toast.success("Asset sent to warranty.")`, close dialog, invalidate issue detail
    - On 404/409: `toast.error(err.message)`; disable submit while pending
    - _Requirements: 8.1–8.6_

  - [x] 6.3 Implement `src/components/issues/CompleteRepairDialog.tsx`
    - TanStack Form with optional `completion_notes` textarea
    - On success: `toast.success("Repair completed. Asset restored to Assigned status.")`, close dialog, invalidate issue detail and asset detail
    - On 404/409: `toast.error(err.message)`; disable submit while pending
    - _Requirements: 9.1–9.6_

  - [x] 6.4 Implement `src/components/issues/RequestReplacementDialog.tsx`
    - TanStack Form with required `replacement_justification` textarea (non-empty, non-whitespace-only)
    - On 400: inline `<FieldError>`; on 404/409: `toast.error(err.message)`
    - On success: `toast.success("Replacement request submitted. Management will review.")`, close dialog
    - Disable submit while pending
    - _Requirements: 10.1–10.8_

  - [ ]* 6.5 Write property test for required field validation blocking submission
    - **Property 11: Required field validation blocks submission**
    - **Validates: Requirements 10.2_

  - [x] 6.6 Implement `src/components/issues/ManagementReviewIssueDialog.tsx`
    - TanStack Form: required `decision` radio group (`APPROVE` / `REJECT`), optional `remarks` textarea, `rejection_reason` textarea required only when `decision === "REJECT"`
    - On APPROVE success: `toast.success("Replacement approved.")`; on REJECT success: `toast.success("Replacement request rejected.")`
    - Invalidate issue detail and pending replacements queries on success
    - On 400: inline `<FieldError>`; on 404/409: `toast.error(err.message)`; disable submit while pending
    - _Requirements: 11.1–11.10_

  - [ ]* 6.7 Write property test for rejection_reason required when decision is REJECT
    - **Property 11: Required field validation blocks submission (rejection_reason)**
    - **Validates: Requirements 11.10**

- [x] 7. Implement `IssueCard` component
  - [x] 7.1 Implement `src/components/issues/IssueCard.tsx`
    - Display: ticket ID (derived from `asset_id` + truncated `timestamp`), `issue_description` as card title, meta row with `asset_id` (HardDrive icon), relative time from `created_at` (Clock icon), `reported_by` (User icon), `IssueStatusBadge`, "View Details" `<Button asChild><Link>` to `/assets/$asset_id/issues/$timestamp`
    - _Requirements: 3.8_

  - [ ]* 7.2 Write property test for IssueCard required fields rendering
    - **Property 6: Issue card renders all required fields**
    - **Validates: Requirements 3.8**

- [x] 8. Rewrite `src/routes/_authenticated/requests.tsx` — IT Admin view
  - [x] 8.1 Replace stub with full implementation
    - Update `MAINTENANCE_ALLOWED` to `['it-admin', 'employee']` only (remove `management`)
    - Keep existing SEO constant and `head` function pattern
    - Add `validateSearch` with Zod schema for `tab` (enum: `requests`, `ongoing`, `history`) and `page` (coerce number, min 1)
    - _Requirements: 3.1, 15.1, 15.5_

  - [x] 8.2 Implement IT Admin view (role === `it-admin`)
    - Page title "Maintenance Hub", subtitle "Manage IT infrastructure maintenance and repair requests."
    - Three stat cards: "Total Active Repairs" (Wrench icon), "Completed Today" (CheckCircle2), "Repairs Due Today" (Calendar) — derive counts from issues data
    - Three tabs synced to URL `tab` param: "Requests" (`TROUBLESHOOTING`), "Ongoing Repairs" (`UNDER_REPAIR`, `SEND_WARRANTY`, `PENDING_APPROVAL`, `REPLACEMENT_APPROVED`, `REPLACEMENT_REJECTED`), "Maintenance History" (`RESOLVED`)
    - Each tab shows count badge; render `IssueCard` list per tab using `useIssues`
    - Pagination showing "Showing X–Y of Z tickets"; page synced to URL `page` param
    - Empty states: "No issues reported." / "No ongoing repairs." / "No maintenance history."
    - Inline `alert-danger` on query error
    - _Requirements: 3.2–3.12_

  - [ ]* 8.3 Write property test for tab filter mapping correctness
    - **Property 5: Tab filter mapping is correct**
    - **Validates: Requirements 3.5, 3.6, 3.7**

  - [ ]* 8.4 Write property test for URL search params round-trip
    - **Property 7: URL search params round-trip for tab and page**
    - **Validates: Requirements 3.12**

  - [x] 8.5 Implement Employee view (role === `employee`) within the same route component
    - Page title "Requests", subtitle "Track and manage your hardware applications and reported issues."
    - "Report Issue" button (warning variant) in header — opens `SubmitIssueDialog` then `UploadIssuePhotosDialog` on success
    - Three stat cards: "Active Requests", "Pending Approval" (warning color), "Resolved Monthly" (success color)
    - TanStack Table with columns: Gadget/Service (asset icon + `asset_id`), Status (`IssueStatusBadge`), Reported By, Date Submitted (`formatDate`), Actions (eye icon `<Button asChild><Link>` to issue detail)
    - Tabs: "All Requests", "Pending" (`ISSUE_REPORTED`), "In Review" (`TROUBLESHOOTING`, `UNDER_REPAIR`, `SEND_WARRANTY`), "Approved" (`REPLACEMENT_APPROVED`, `RESOLVED`), "Rejected" (`REPLACEMENT_REJECTED`)
    - Pagination showing "Showing 1 to N of M requests"
    - Inline `alert-danger` on query error
    - `createColumnHelper` outside component; memoize `data` and `columns` with `useMemo`
    - _Requirements: 4.1–4.7_

  - [ ]* 8.6 Write property test for employee table required columns
    - **Property 8: Employee table renders all required columns**
    - **Validates: Requirements 4.4**

- [x] 9. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Create Issue Detail route and page
  - [x] 10.1 Create `src/routes/_authenticated/assets.$asset_id.issues.$timestamp.tsx`
    - `ALLOWED: UserRole[] = ['it-admin', 'management', 'employee']`
    - SEO constant with `title: 'Issue Detail'`, `path: '/assets/issues/detail'`
    - `beforeLoad` guard redirecting unauthorized roles to `/unauthorized`
    - `head` function with `noindex, nofollow` robots override
    - Extract `asset_id` and `timestamp` from `Route.useParams()`
    - _Requirements: 5.1, 15.1–15.3_

  - [x] 10.2 Implement `IssueDetailPage` component
    - Call `useIssueDetail(assetId, timestamp)`; show centered spinner while loading; show inline `alert-danger` on error
    - "Issue Info" section: `issue_description`, `action_path` rendered as "Repair" / "Replacement" / "Pending"
    - "Evidence Photos" section: clickable thumbnails from `issue_photo_urls`; "No photos attached." when empty/null
    - "Status" section: `IssueStatusBadge`, `created_at` via `formatDate`, `reported_by`
    - "Triage" section: render only when `triaged_by` is populated; show `triaged_by` and `triaged_at`
    - "Repair Details" section: render only when `action_path === "REPAIR"`; show populated fields from `repair_notes`, `warranty_notes`, `warranty_sent_at`, `completed_at`, `completion_notes`, `resolved_by`, `resolved_at`
    - "Replacement Details" section: render only when `action_path === "REPLACEMENT"`; show `replacement_justification`, `resolved_by`, `resolved_at`
    - "Management Review" section: render only when `management_reviewed_by` is populated; show `management_reviewed_by`, `management_reviewed_at`, `management_rejection_reason`, `management_remarks`
    - _Requirements: 5.2–5.11_

  - [ ]* 10.3 Write property test for issue detail conditional sections
    - **Property 9: Issue detail renders correct sections based on data**
    - **Validates: Requirements 5.3–5.9**

  - [x] 10.4 Implement conditional action buttons on Issue Detail
    - Read role via `useCurrentUserRole()` and issue status from detail response
    - `it-admin` + `TROUBLESHOOTING` → "Start Repair" (opens `StartRepairDialog`) + "Request Replacement" (opens `RequestReplacementDialog`)
    - `it-admin` + `UNDER_REPAIR` → "Send to Warranty" (opens `SendWarrantyDialog`) + "Complete Repair" (opens `CompleteRepairDialog`)
    - `it-admin` + `SEND_WARRANTY` → "Complete Repair" (opens `CompleteRepairDialog`)
    - `management` + `PENDING_APPROVAL` → "Review Replacement Request" (opens `ManagementReviewIssueDialog`)
    - No buttons for any other role/status combination
    - _Requirements: 6.1–6.5_

  - [ ]* 10.5 Write property test for action button visibility matrix
    - **Property 10: Action button visibility matches role-status matrix**
    - **Validates: Requirements 6.1–6.5**

- [x] 11. Create Pending Replacements route and page
  - [x] 11.1 Create `src/routes/_authenticated/pending-replacements.tsx`
    - `ALLOWED: UserRole[] = ['management']`
    - SEO constant with `title: 'Pending Replacements'`, `path: '/pending-replacements'`
    - `validateSearch` with Zod schema: `page` (coerce number, min 1, optional), `page_size` (coerce number, optional)
    - `beforeLoad` guard redirecting non-management roles to `/unauthorized`
    - `head` function with `noindex, nofollow` robots override
    - _Requirements: 12.1, 12.7, 15.1–15.5_

  - [x] 11.2 Implement `PendingReplacementsPage` component
    - Call `usePendingReplacements(page, pageSize)` with page/pageSize from search params
    - TanStack Table with `createColumnHelper` outside component; memoize `data` and `columns`
    - Columns: Asset ID (`<Link to="/assets/$asset_id">` linked), Issue Description (truncated), Action Path, Replacement Justification (truncated), Reported By, Triaged By, Resolved By, Created At (`formatDate`), Actions (eye icon `<Button asChild><Link>` to `/assets/$asset_id/issues/$timestamp`)
    - Pagination controls below table
    - Empty state: "No pending replacement requests."
    - Inline `alert-danger` on query error
    - _Requirements: 12.2–12.6_

  - [ ]* 11.3 Write property test for pending replacements table required columns
    - **Property 12: Pending replacements table renders all required columns**
    - **Validates: Requirements 12.3**

- [x] 12. Add Issues tab and Report Issue button to Asset Detail page
  - [x] 12.1 Add Issues tab to `src/routes/_authenticated/assets.$asset_id.tsx`
    - Extend `assetDetailSearchSchema` with `issues_tab` and `issues_page` params
    - Add `tab` enum value `'issues'` to the existing tab schema
    - Show Issues tab when `role === 'it-admin'` OR (`role === 'employee'` AND `isCurrentUserAssignee`)
    - Render `IssueCard` list inside the Issues tab using `useIssues(assetId, filters, page)`
    - _Requirements: 3.8, 4.4_

  - [x] 12.2 Add "Report Issue" button to Asset Detail page
    - Show button when `role === 'employee'` AND `asset.status === 'ASSIGNED'` AND `isCurrentUserAssignee`
    - Button opens `SubmitIssueDialog`; on success open `UploadIssuePhotosDialog` with the returned `timestamp`
    - _Requirements: 1.1_

- [x] 13. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- `IssueStatus.PENDING_APPROVAL` in `types.ts` corresponds to `REPLACEMENT_REQUIRED` in requirements — always use the `types.ts` value in code
- Never edit `routeTree.gen.ts` — it is auto-generated
- Use `formatDate` from `#/lib/utils` for all date display
- All mutations must have `onError` handlers — no silent failures
- For the Ongoing Repairs tab, fetch each status separately and merge client-side, or pass multiple status params if the API supports it
