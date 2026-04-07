# Implementation Plan: Asset Assignment & Handover

## Overview

Implement the frontend for Phase 2 asset assignment and handover. This adds assignment, acceptance, cancellation, and signature audit flows using modal dialogs from existing pages. All hooks go in `src/hooks/use-assets.ts`, types in `src/lib/models/types.ts`, query keys in `src/lib/query-keys.ts`. No new route files needed.

## Tasks

- [ ] 1. Add types, query keys, and API hooks
  - [x] 1.1 Add `ListSignaturesFilter`, `ListSignaturesResponse`, and `AssignAssetRequest`/`AssignAssetResponse`/`CancelAssignmentResponse`/`GetHandoverFormResponse`/`GenerateSignatureUploadUrlResponse`/`AcceptHandoverRequest`/`AcceptHandoverResponse`/`SignatureItem` types to `src/lib/models/types.ts` (only add types not already present — `ListSignaturesFilter` and `ListSignaturesResponse` are new)
    - `ListSignaturesFilter` extends `PaginatedAPIFilter` with optional `assignment_date_from` and `assignment_date_to`
    - `ListSignaturesResponse` is `PaginatedAPIResponse<SignatureItem>`
    - Verify existing types match the design; add any missing ones
    - _Requirements: 8.1_

  - [x] 1.2 Extend query key factory in `src/lib/query-keys.ts`
    - Add `handoverForm: (assetId: string) => [...queryKeys.assets.all(), 'handover-form', assetId] as const`
    - Add `signatures: (employeeId: string, params: { page: number; page_size: number; filters?: any }) => [...queryKeys.assets.all(), 'signatures', employeeId, params] as const`
    - _Requirements: 8.8_

  - [x] 1.3 Add `useAssignAsset` mutation hook to `src/hooks/use-assets.ts`
    - Calls `POST /assets/{asset_id}/assign` with `{ employee_id, notes }`
    - Invalidates `queryKeys.assets.all()` on settled
    - _Requirements: 8.2_

  - [x] 1.4 Add `useCancelAssignment` mutation hook to `src/hooks/use-assets.ts`
    - Calls `DELETE /assets/{asset_id}/cancel-assignment`
    - Invalidates `queryKeys.assets.all()` on settled
    - _Requirements: 8.3_

  - [x] 1.5 Add `useAcceptHandover` mutation hook to `src/hooks/use-assets.ts`
    - Calls `PUT /assets/{asset_id}/accept` with `{ signature_s3_key }`
    - Invalidates `queryKeys.assets.all()` on settled
    - _Requirements: 8.4_

  - [x] 1.6 Add `useHandoverForm` mutation hook to `src/hooks/use-assets.ts`
    - Calls `GET /assets/{asset_id}/assign-pdf-form` (mutation because it's on-demand for presigned URL)
    - No cache invalidation
    - _Requirements: 8.5_

  - [x] 1.7 Add `useSignatureUploadUrl` mutation hook to `src/hooks/use-assets.ts`
    - Calls `POST /assets/{asset_id}/signature-upload-url`
    - No cache invalidation
    - _Requirements: 8.6_

  - [x] 1.8 Add `useEmployeeSignatures` query hook to `src/hooks/use-assets.ts`
    - Calls `GET /users/{employee_id}/signatures` with pagination and date filter params
    - Uses `queryKeys.assets.signatures(employeeId, params)` for cache key
    - `staleTime: 60_000`
    - _Requirements: 8.7_

  - [ ]* 1.9 Write property test for cache invalidation (Property 4)
    - **Property 4: Successful assignment mutations invalidate asset caches**
    - **Validates: Requirements 1.8, 3.14, 4.5**
    - Test file: `src/__tests__/properties/asset-assignment-handover.test.ts`
    - Verify `useAssignAsset`, `useCancelAssignment`, `useAcceptHandover` all call `invalidateQueries` with key matching `queryKeys.assets.all()` on settled

- [ ] 2. Implement handover state detection and action visibility utilities
  - [x] 2.1 Create `getHandoverState` utility function
    - Add to a new file `src/lib/asset-utils.ts` (or inline in hooks)
    - Input: `(status: AssetStatus, assignmentDate: string | undefined)`
    - Returns: `'pending' | 'completed' | 'available' | 'none'`
    - Logic: `IN_STOCK` + date → `'pending'`, `ASSIGNED` + date → `'completed'`, `IN_STOCK` + no date → `'available'`, else → `'none'`
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 2.2 Create `getVisibleActions` utility function
    - Input: `(role: UserRole, status: AssetStatus, handoverState: string, isAssignedUser: boolean)`
    - Returns: array of action identifiers (`'assign'`, `'view-handover-form'`, `'cancel-assignment'`, `'accept-asset'`)
    - Implements the full visibility matrix from the design (Property 2)
    - _Requirements: 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10_

  - [ ]* 2.3 Write property test for handover state classification (Property 1)
    - **Property 1: Handover state classification is deterministic and exhaustive**
    - **Validates: Requirements 6.1, 6.2, 6.3**
    - Generate random `(AssetStatus, assignmentDate | undefined)` tuples via fast-check
    - Verify exactly one of `'pending'`, `'completed'`, `'available'`, `'none'` is returned

  - [ ]* 2.4 Write property test for action visibility (Property 2)
    - **Property 2: Action visibility is consistent with role, status, and handover state**
    - **Validates: Requirements 1.1, 2.1, 2.2, 3.1, 4.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 9.2**
    - Generate random `(UserRole, AssetStatus, handoverState, isAssignedUser)` tuples via fast-check
    - Verify returned action set matches expected visibility rules

- [x] 3. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Implement AssignAssetModal component
  - [x] 4.1 Create `src/components/assets/AssignAssetModal.tsx`
    - Shadcn Dialog with `open`/`onOpenChange` props and `assetId` prop
    - `<Autocomplete>` for employee search using `useUsers` with `status=active&role=employee` filter
    - Optional notes `<Textarea>`
    - Confirm button in `<DialogFooter>`, disabled while mutation is pending with `<Spinner>`
    - On success: toast notification with employee name, offer to open PDF via `presigned_url`, call `onOpenChange(false)`
    - On error: display API error message inline via `alert-danger` class
    - Handle 409 (already assigned, in progress, wrong status) and 404 (employee not found) errors
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11, 1.12, 1.13_

  - [ ]* 4.2 Write unit tests for AssignAssetModal
    - Test: renders employee selector, submits correct payload, shows success toast, shows error messages for 409/404
    - _Requirements: 1.3, 1.5, 1.6, 1.9, 1.10, 1.11, 1.12_

- [ ] 5. Implement SignatureCapture component
  - [x] 5.1 Create `src/components/assets/SignatureCapture.tsx`
    - Wraps `react-signature-canvas` library
    - Props: `{ onSignatureReady: (blob: Blob) => void; disabled?: boolean }`
    - Canvas drawing pad with Clear button
    - Exports signature as PNG Blob via `onSignatureReady` callback
    - File upload fallback for PNG signature images
    - _Requirements: 3.7_

- [ ] 6. Implement AcceptHandoverDialog component
  - [x] 6.1 Create `src/components/assets/AcceptHandoverDialog.tsx`
    - Multi-step wizard (3 steps) managed by local `step` state
    - Props: `{ open, onOpenChange, assetId, asset: { brand?, model?, serial_number?, status } }`
    - Step 1: Asset summary + "Download Handover Form" button (calls `useHandoverForm`, opens PDF in new tab) + review checkbox (disabled until form viewed, enables Step 2 navigation)
    - Step 2: `<SignatureCapture>` component + upload logic (calls `useSignatureUploadUrl`, PUTs to S3 presigned URL with `Content-Type: image/png`, stores `s3_key` in state, enables Step 3)
    - Step 3: "Agree & Accept Asset" button (calls `useAcceptHandover` with `{ signature_s3_key }`)
    - On success: show confirmation with `signed_form_url` link
    - Error handling: 409 (form not generated → "Contact IT Admin"), 409 (wrong state), 400 (signature not found → retry prompt)
    - Disable action buttons + show spinner while any API request is in progress
    - Handle presigned URL expiry (403 from S3 → show refresh prompt)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14, 3.15, 3.16, 3.17, 3.18, 10.1, 10.2_

  - [ ]* 6.2 Write unit tests for AcceptHandoverDialog
    - Test: step progression (1→2→3), checkbox gating, signature upload flow, accept API call, error states
    - _Requirements: 3.3, 3.6, 3.12, 3.15, 3.16, 3.17_

- [ ] 7. Implement CancelAssignmentDialog component
  - [x] 7.1 Create `src/components/assets/CancelAssignmentDialog.tsx`
    - Destructive confirmation dialog with warning message: "Are you sure you want to cancel this assignment? The asset will return to IN_STOCK."
    - Props: `{ open, onOpenChange, assetId }`
    - Uses `useCancelAssignment` mutation hook
    - On success: toast notification, close dialog
    - On error: display API error message inline (409 already accepted, 404 no pending assignment)
    - Disable confirm/cancel buttons + show spinner while request is in progress
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

  - [ ]* 7.2 Write unit tests for CancelAssignmentDialog
    - Test: confirmation message, API call on confirm, success toast, error messages for 409/404
    - _Requirements: 4.2, 4.4, 4.6, 4.7_

- [x] 8. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Update asset detail page with conditional action buttons and route guard
  - [x] 9.1 Expand route guard in `src/routes/_authenticated/assets.$asset_id.tsx`
    - Add `'employee'` to `DETAIL_ALLOWED` array
    - _Requirements: 9.1_

  - [x] 9.2 Add `assignment_date` to route search params validation
    - Extend the route's `validateSearch` with optional `assignment_date` Zod field
    - Read `assignment_date` from search params to derive handover state via `getHandoverState`
    - _Requirements: 6.4_

  - [x] 9.3 Add conditional action buttons to asset detail modal
    - Use `useCurrentUserRole()` and `getVisibleActions()` to determine which buttons to render
    - Render `<AssignAssetModal>`, `<AcceptHandoverDialog>`, `<CancelAssignmentDialog>` as needed
    - "View Handover Form" button calls `useHandoverForm` and opens PDF in new tab
    - Employee sees read-only asset info without management actions (approve/reject)
    - Handle presigned URL expiry for handover form (403 → refresh prompt)
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 4.1, 7.10, 9.2, 9.3, 10.1, 10.2_

- [ ] 10. Update asset list page with dropdown menu actions
  - [x] 10.1 Refactor actions column in `src/routes/_authenticated/assets.tsx`
    - Replace current inline action buttons with the dropdown menu (⋯) pattern per table-actions steering protocol
    - Keep "View Details" eye button
    - Add `<DropdownMenu>` with conditional items based on role + status + handover state using `getVisibleActions()`
    - Pass `assignment_date` as search param when navigating to detail page
    - Dropdown items: "Assign to Employee", "View Handover Form", "Cancel Assignment", "Accept Asset"
    - Hide dropdown trigger when no actions available
    - Open `<AssignAssetModal>` and `<CancelAssignmentDialog>` from list page row actions
    - Move existing "Review" button for management into the dropdown
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9_

- [ ] 11. Implement EmployeeSignaturesSection component
  - [x] 11.1 Create `src/components/assets/EmployeeSignaturesSection.tsx`
    - Props: `{ employeeId: string }`
    - Uses `useEmployeeSignatures` hook with pagination and date range filters
    - `<DataTable>` with columns: Asset ID (linked to asset detail), Brand, Model, Assignment Date (formatted via `formatDate`), Signed At (formatted via `formatDate`), Signature (clickable thumbnail/link)
    - Pagination controls matching paginated API response
    - Date range filter inputs (`assignment_date_from`, `assignment_date_to`) inside a filter Dialog per filter-ui steering protocol
    - Empty state: "No handover signatures on record."
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [ ]* 11.2 Write property test for signature table row content (Property 3)
    - **Property 3: Signature table rows contain all required formatted fields**
    - **Validates: Requirements 5.3**
    - Generate random `SignatureItem` objects with arbitrary strings/dates via fast-check
    - Verify rendered output contains all required fields (asset_id as link, brand or dash, model or dash, formatted dates, signature URL as clickable element)

- [ ] 12. Wire EmployeeSignaturesSection into the users page
  - [x] 12.1 Add `<EmployeeSignaturesSection>` to the user detail view
    - Conditionally render when `role === 'it-admin'` and the viewed user has `role === 'employee'`
    - Pass the employee's `user_id` as `employeeId` prop
    - _Requirements: 5.1_

- [x] 13. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All property tests use fast-check with minimum 100 iterations
- Property test file: `src/__tests__/properties/asset-assignment-handover.test.ts`
