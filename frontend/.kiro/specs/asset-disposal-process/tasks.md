# Implementation Plan: Asset Disposal Process

## Overview

Implement the complete asset disposal workflow frontend: initiate disposal (IT Admin), management review (approve/reject), complete disposal (IT Admin), disposal detail page, pending disposals tab, all disposals list page, and immutability enforcement for disposed assets. All code uses TypeScript with TanStack Router, TanStack Query, TanStack Form, TanStack Table, Shadcn UI, Zod, and sonner.

## Tasks

- [x] 1. Set up disposal infrastructure (query keys, permissions, hooks)
  - [x] 1.1 Extend `src/lib/query-keys.ts` with `disposals` namespace
    - Add `disposals.all`, `disposals.list`, `disposals.detail`, and `disposals.pendingDisposals` key factories
    - Import `ListDisposalsFilter` and `ListPendingDisposalsFilter` from types
    - _Requirements: 7.2, 7.4_

  - [x] 1.2 Add `getDisposalDetailPermissions` to `src/lib/permissions.ts`
    - Create `DisposalDetailContext` type with `role` and `assetStatus`
    - Create `DisposalDetailPermissions` type with `canInitiateDisposal`, `canManagementReview`, `canCompleteDisposal`
    - Implement permission logic: `canInitiateDisposal` true when role is `it-admin` AND status in `DISPOSAL_REVIEW`, `IN_STOCK`, `DAMAGED`, `REPAIR_REQUIRED`; `canManagementReview` true when role is `management` AND status is `DISPOSAL_PENDING`; `canCompleteDisposal` true when role is `it-admin` AND status is `DISPOSAL_APPROVED`
    - Extend `getAssetDetailPermissions` to include `showInitiateDisposalButton` flag
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ]* 1.3 Write property test for disposal permission flags (Property 1)
    - **Property 1: Disposal permission flags are correct for all role/status combinations**
    - Generate all (UserRole, AssetStatus) pairs using `fc.constantFrom`
    - Assert `canInitiateDisposal`, `canManagementReview`, `canCompleteDisposal` match the specification exactly
    - Assert `showInitiateDisposalButton` matches `canInitiateDisposal` conditions
    - **Validates: Requirements 1.1, 1.9, 1.10, 4.1, 4.10, 5.1, 5.10, 8.2, 8.3, 8.4, 8.5, 8.6**

  - [x] 1.4 Create `src/hooks/use-disposals.ts` with all query and mutation hooks
    - `useDisposalDetail(assetId, disposalId)` — GET `/assets/{asset_id}/disposals/{disposal_id}`
    - `useDisposals(filters, page, pageSize)` — GET `/disposals` with query params
    - `usePendingDisposals(page, pageSize)` — GET `/disposals/pending` with query params
    - `useInitiateDisposal(assetId)` — POST `/assets/{asset_id}/disposals`, invalidates asset detail + disposal list + pending disposals
    - `useManagementReviewDisposal(assetId, disposalId)` — PUT management-review endpoint, invalidates disposal detail + pending disposals
    - `useCompleteDisposal(assetId, disposalId)` — PUT complete endpoint, invalidates asset detail + disposal detail + disposal list
    - All hooks follow existing patterns from `use-issues.ts` and `use-returns.ts`
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 2. Implement status badges and labels
  - [x] 2.1 Create `src/components/disposals/DisposalStatusBadge.tsx`
    - Map asset statuses to Badge variants: `DISPOSAL_REVIEW` → warning, `DISPOSAL_PENDING` → warning, `DISPOSAL_APPROVED` → info, `DISPOSAL_REJECTED` → danger, `DISPOSED` → default
    - Use `AssetStatusLabels` from `labels.ts` for display text
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ]* 2.2 Write property test for disposal status badge mapping (Property 5)
    - **Property 5: Disposal status badge mapping is consistent**
    - Generate random disposal-related AssetStatus values, FinanceNotificationStatus values, and data wipe boolean/null values
    - Assert each maps to the correct variant and label per the design spec
    - **Validates: Requirements 9.4, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7**

- [x] 3. Checkpoint — Ensure infrastructure compiles
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement Initiate Disposal Dialog and Asset Detail page integration
  - [x] 4.1 Create `src/components/disposals/InitiateDisposalDialog.tsx`
    - TanStack Form with Zod validation: `disposal_reason` (required, non-empty trimmed) and `justification` (required, non-empty trimmed)
    - Read-only asset summary section showing brand, model, serial number, cost (formatNumber), category
    - Calls `useInitiateDisposal` mutation on submit
    - Success: `toast.success("Disposal request submitted. Awaiting management approval.")`, close dialog
    - Error handling: 400 → `toast.error(err.message)`, 404 → `toast.error("Asset not found")`, 409 → `toast.error("Asset is not in a valid status for disposal")`
    - Form resets on dialog close
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

  - [ ]* 4.2 Write property test for disposal form validation (Property 2)
    - **Property 2: Disposal form validation rejects whitespace-only inputs**
    - Generate whitespace-only strings and assert validation rejects them for both fields
    - Generate strings with at least one non-whitespace character and assert validation accepts them
    - **Validates: Requirements 1.3, 4.5**

  - [x] 4.3 Integrate disposal into Asset Detail page (`src/routes/_authenticated/assets.$asset_id.tsx`)
    - Import `InitiateDisposalDialog` and wire open/close state
    - Use extended `getAssetDetailPermissions` to get `showInitiateDisposalButton`
    - Pass `showInitiateDisposal` and `onInitiateDisposal` props to `QuickActionsCard`
    - _Requirements: 1.1, 1.9, 1.10_

  - [x] 4.4 Update `QuickActionsCard.tsx` to support disposal button
    - Add `showInitiateDisposal?: boolean` and `onInitiateDisposal?: () => void` props
    - Render "Initiate Disposal" button with Trash2 icon when `showInitiateDisposal` is true
    - _Requirements: 1.1_

  - [x] 4.5 Add immutability enforcement for DISPOSED assets on Asset Detail page
    - When `asset.status === 'DISPOSED'`, display a prominent banner: "This asset has been disposed and is locked. No further actions are permitted."
    - When `asset.status === 'DISPOSED'`, hide all action buttons (QuickActionsCard, tabs, etc.)
    - _Requirements: 9.1, 9.2_

- [x] 5. Checkpoint — Verify initiate disposal flow compiles
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement Disposal Detail page route
  - [x] 6.1 Create `src/routes/_authenticated/assets.$asset_id.disposals.$disposal_id.tsx`
    - Route with `beforeLoad` guard: only `it-admin` and `management` roles allowed
    - SEO metadata with `noindex, nofollow`
    - Call `useDisposalDetail` hook to fetch disposal data
    - Display sections: Disposal Info (reason, justification, initiated by, initiated at), Asset Specs (brand, model, serial number, product description, cost with formatNumber, purchase date with formatDate — "N/A" for null fields)
    - Conditional Management Review section (visible when `management_reviewed_at` is present): reviewed by, reviewed at, remarks, rejection reason
    - Conditional Completion section (visible when `completed_at` is present): disposal date, data wipe confirmed badge, completed by, completed at
    - Conditional Finance Notification section (visible when `finance_notification_sent` is true): status badge, notified at
    - Lock banner when `is_locked` is true: "This asset has been disposed and is now locked. No further actions are allowed." — hide all action buttons
    - Skeleton loading state, inline error display
    - Breadcrumb navigation: Assets > {asset_id} > Disposal > {disposal_id}
    - Conditional action buttons: Approve/Reject (management + DISPOSAL_PENDING), Complete Disposal (it-admin + DISPOSAL_APPROVED)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_

  - [ ]* 6.2 Write property test for conditional detail sections (Property 3)
    - **Property 3: Conditional detail sections match data presence**
    - Generate `GetDisposalDetailsResponse` objects with random null/present fields
    - Assert Management Review section visible iff `management_reviewed_at` is present
    - Assert Completion section visible iff `completed_at` is present
    - Assert Finance Notification section visible iff `finance_notification_sent` is true
    - **Validates: Requirements 3.4, 3.5, 3.6**

  - [ ]* 6.3 Write property test for locked state hides all actions (Property 4)
    - **Property 4: Locked disposals and disposed assets hide all actions**
    - Generate disposal/asset data with `is_locked=true` or `status=DISPOSED`
    - Assert all action buttons are hidden and lock banner is displayed
    - **Validates: Requirements 3.7, 9.1, 9.2, 9.3**

  - [ ]* 6.4 Write property test for disposal detail field rendering (Property 7)
    - **Property 7: Disposal detail renders all fields with N/A fallback for nulls**
    - Generate `GetDisposalDetailsResponse` with nullable asset_specs fields
    - Assert null fields render "N/A", present fields render their values (formatNumber for cost, formatDate for purchase_date)
    - **Validates: Requirements 3.2, 3.3**

- [x] 7. Implement Management Review dialogs (Approve/Reject)
  - [x] 7.1 Create `src/components/disposals/ApproveDisposalDialog.tsx`
    - Dialog with optional "Remarks" textarea
    - Calls `useManagementReviewDisposal` with `decision: "APPROVE"` and optional remarks
    - Success: `toast.success("Disposal request approved.")`, close dialog
    - Error handling: 400 → toast, 409 → toast "Disposal is not in DISPOSAL_PENDING status"
    - _Requirements: 4.2, 4.3, 4.4, 4.8, 4.9_

  - [x] 7.2 Create `src/components/disposals/RejectDisposalDialog.tsx`
    - Dialog with required "Rejection Reason" textarea (validated non-empty, trimmed)
    - Calls `useManagementReviewDisposal` with `decision: "REJECT"` and `rejection_reason`
    - Success: `toast.success("Disposal request rejected.")`, close dialog
    - Error handling: 400 → toast, 409 → toast
    - _Requirements: 4.5, 4.6, 4.7, 4.8, 4.9_

  - [x] 7.3 Wire Approve/Reject dialogs into Disposal Detail page
    - Import both dialogs, manage open/close state
    - Show buttons only when `canManagementReview` is true (from `getDisposalDetailPermissions`)
    - _Requirements: 4.1, 4.10_

- [x] 8. Implement Complete Disposal dialog
  - [x] 8.1 Create `src/components/disposals/CompleteDisposalDialog.tsx`
    - TanStack Form with date picker for "Disposal Date" (required, YYYY-MM-DD) and "Data Wipe Confirmed" checkbox (required, must be true)
    - Disable submit button and show inline warning when checkbox unchecked: "You must confirm that the device data has been wiped before completing the disposal."
    - Read-only display of disposal reason and justification for context
    - Calls `useCompleteDisposal` mutation on submit
    - Success: `toast.success("Disposal completed. Asset is now disposed.")` + conditional finance notification toasts (COMPLETED → info, NO_FINANCE_USERS → warning, FAILED → warning)
    - Error handling: 400 → toast, 409 → toast "Disposal is not in DISPOSAL_APPROVED status"
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9_

  - [ ]* 8.2 Write property test for data wipe checkbox gating (Property 9)
    - **Property 9: Data wipe checkbox gates form submission**
    - Generate random (data_wipe_confirmed, disposal_date) pairs
    - Assert submit disabled and warning visible when `data_wipe_confirmed` is false
    - Assert submit enabled when `data_wipe_confirmed` is true and date is valid
    - **Validates: Requirements 5.3**

  - [x] 8.3 Wire Complete Disposal dialog into Disposal Detail page
    - Import dialog, manage open/close state
    - Show button only when `canCompleteDisposal` is true
    - _Requirements: 5.1, 5.10_

- [x] 9. Checkpoint — Verify disposal detail page and all dialogs compile
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement Pending Disposals tab in Approvals page
  - [x] 10.1 Create `DisposalsTabContent` component for the Approvals page
    - Call `usePendingDisposals` hook with page/pageSize
    - DataTable with columns: Asset ID (link to disposal detail), Brand/Model (from `asset_specs`, "N/A" for null), Serial Number (from `asset_specs`, "N/A" if null), Disposal Reason, Justification (truncated), Initiated By, Initiated At (formatDate), Review action button (Eye icon linking to disposal detail)
    - Pagination controls synced to URL search params
    - Empty state: "No pending disposal requests."
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 10.2 Write property test for pending disposals table rendering (Property 6)
    - **Property 6: Pending disposals table renders all required fields**
    - Generate random `PendingDisposalItem` with nullable `asset_specs` fields
    - Assert all required fields are present in the rendered row, with "N/A" for null asset_specs values
    - **Validates: Requirements 2.3**

  - [x] 10.3 Integrate `DisposalsTabContent` into `src/routes/_authenticated/approvals.tsx`
    - Update the `disposals` tab in `ALL_TABS` to have `roles: ['management']` (per Req 2.7)
    - Import and render `DisposalsTabContent` in the disposals TabsContent
    - _Requirements: 2.1, 2.7_

- [x] 11. Implement All Disposals list page and navigation
  - [x] 11.1 Create `src/routes/_authenticated/disposals.tsx` route
    - Route with `beforeLoad` guard: only `it-admin` role allowed
    - SEO metadata with `noindex, nofollow`
    - Zod-validated search schema for: `page`, `page_size`, `status` (DISPOSAL_PENDING, DISPOSAL_APPROVED, DISPOSAL_REJECTED, DISPOSED), `disposal_reason`, `date_from`, `date_to`
    - Call `useDisposals` hook with filters and pagination
    - DataTable with columns: Asset ID (link to disposal detail), Disposal Reason, Justification (truncated), Initiated By, Initiated At (formatDate), Status (DisposalStatusBadge), Reviewed By ("—" if null), Reviewed At (formatDate, "—" if null), Disposal Date (formatDate, "—" if null), actions column (Eye icon link to disposal detail)
    - Filter dialog with: status dropdown, disposal reason text input, date_from/date_to date pickers
    - Pagination synced to URL search params
    - Empty state: "No disposal records found."
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

  - [ ]* 11.2 Write property test for all disposals table rendering (Property 8)
    - **Property 8: All disposals table renders all required columns**
    - Generate random `DisposalListItem` with nullable fields
    - Assert all required columns are present, with "—" for null optional fields
    - **Validates: Requirements 6.3**

  - [ ]* 11.3 Write property test for disposal list filter URL round-trip (Property 10)
    - **Property 10: Disposal list filter URL round-trip**
    - Generate random valid filter combinations matching the Zod search schema
    - Serialize to URL search params and parse back, assert values are identical
    - **Validates: Requirements 6.5**

  - [x] 11.4 Add "Disposals" navigation item to Header for IT Admin
    - Add `{ label: 'Disposals', to: '/disposals' }` to `NAV_ITEMS_BY_ROLE['it-admin']` in `src/components/general/Header.tsx`
    - _Requirements: 6.1, 6.7_

- [x] 12. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All types (`InitiateDisposalRequest`, `ManagementReviewDisposalRequest`, `CompleteDisposalRequest`, `GetDisposalDetailsResponse`, `ListDisposalsResponse`, `ListPendingDisposalsResponse`, etc.) are already defined in `src/lib/models/types.ts`
- All labels (`AssetStatusLabels`, `FinanceNotificationStatusLabels`) are already defined in `src/lib/models/labels.ts`
- The codebase uses `#/` path alias for imports from `src/`
