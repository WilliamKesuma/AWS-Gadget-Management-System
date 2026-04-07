# Implementation Plan: Asset Creation Flow

## Overview

Implement the Asset Creation Flow in phases: data layer first (types, query keys, labels, hooks), then modal components (upload + polling), then full-page routes (confirm, success, approve), and finally wire everything into the existing assets list page.

## Tasks

- [x] 1. Extend data layer — query keys, labels, and API types
  - Add `assets` key factory to `src/lib/query-keys.ts` with `all()`, `list(params)`, and `scanJob(scanJobId)` keys
  - Add `ASSET_STATUS_LABELS` record to `src/lib/models/labels.ts` covering all `AssetStatus` values
  - Verify `AssetStatus`, `AssetItem`, `ListAssetsResponse`, `GenerateUploadUrlsRequest`, `GenerateUploadUrlsResponse`, `GetScanResultsResponse`, `CreateAssetRequest`, `CreateAssetResponse`, `ApproveAssetRequest`, `ApproveAssetResponse`, and `ExtractedFieldValue` types exist in `src/lib/models/types.ts`; add any that are missing
  - _Requirements: 9.1, 9.5, 11.6, 11.7_

- [x] 2. Implement all asset hooks in `src/hooks/use-assets.ts`
  - [x] 2.1 Implement `useAssets(pageSize?)` — `useQuery` for `GET /assets` with `page` and `status` filter state, `staleTime: 60_000`, keys from factory
    - _Requirements: 9.1, 9.4, 9.6_
  - [ ]* 2.2 Write property test for `useAssets` pagination and filter params (Property 10)
    - **Property 10: Asset List Pagination and Filter Params**
    - **Validates: Requirements 9.1, 9.4, 9.6**
  - [x] 2.3 Implement `useUploadAsset()` — `useMutation` that POSTs `GenerateUploadUrlsRequest` to `/assets/uploads` via `apiClient`, then parallel-PUTs each file to its presigned URL using plain `fetch` with no `Authorization` header
    - _Requirements: 4.1, 4.2, 4.3_
  - [ ]* 2.4 Write property test for `useUploadAsset` auth header exclusion (Property 3)
    - **Property 3: Auth Header Exclusion on Presigned URLs**
    - **Validates: Requirements 4.3**
  - [ ]* 2.5 Write property test for `useUploadAsset` upload flow sequencing (Property 4)
    - **Property 4: Upload Flow Sequencing**
    - **Validates: Requirements 4.1, 4.2**
  - [x] 2.6 Implement `useScanJob(scanJobId)` — `useQuery` polling `GET /assets/scan/{scanJobId}` with `refetchInterval: (query) => query.state.data?.status === 'PROCESSING' ? 3000 : false` and `enabled: !!scanJobId`
    - _Requirements: 5.1, 5.9_
  - [ ]* 2.7 Write unit tests for `useScanJob` refetchInterval logic
    - Assert returns `3000` for `PROCESSING`, `false` for `COMPLETED` and `SCAN_FAILED`
    - _Requirements: 5.1_
  - [ ]* 2.8 Write property test for polling interval cleanup (Property 5)
    - **Property 5: Polling Interval Cleanup**
    - **Validates: Requirements 5.9**
  - [x] 2.9 Implement `useCreateAsset()` — `useMutation` that POSTs `CreateAssetRequest` to `/assets` via `apiClient`
    - _Requirements: 7.1_
  - [x] 2.10 Implement `useApproveAsset(assetId)` — `useMutation` with `mutationKey: ['assets', 'approve', assetId]` that PUTs `ApproveAssetRequest` to `/assets/{assetId}/approve`; invalidate `queryKeys.assets.all()` in `onSettled`
    - _Requirements: 11.6, 11.7_

- [x] 3. Checkpoint — ensure hooks compile cleanly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement `UploadStep` component (`src/components/assets/UploadStep.tsx`)
  - [x] 4.1 Build `DragDropZone` sub-component (or inline) accepting `accept`, `maxFiles`, `label`, `files`, `onFilesChange` props; display file name, size, and "Ready to process" status once a file is selected
    - _Requirements: 3.1, 3.2, 3.3_
  - [x] 4.2 Render invoice zone (PDF/image, max 1) and photos zone (image, 1–5) with correct labels; render "UPLOADED FILES" list below with file icon, name, size, status, and trash icon per file
    - _Requirements: 3.1, 3.2, 3.4, 3.5_
  - [x] 4.3 Implement client-side validation: no invoice → inline error; 0 or >5 photos → inline error; invalid MIME type → inline error; all without calling the API
    - _Requirements: 3.6, 3.7, 3.8, 3.9_
  - [ ]* 4.4 Write property test for upload validation gate (Property 2)
    - **Property 2: Upload Validation Gate**
    - **Validates: Requirements 3.6, 3.7, 3.8, 3.9**
  - [x] 4.5 Wire `useUploadAsset` mutation to the "Upload & Scan" button; disable button and show loading indicator while `isPending`; call `onUploadComplete(uploadSessionId, scanJobId)` on success; display `ApiError.message` inline on error
    - _Requirements: 4.1, 4.4, 4.5, 4.6, 4.7_
  - [x] 4.6 Render "Cancel" button (outlined, destructive) and "Upload & Scan" button (filled, primary) in the footer; wire Cancel to `onCancel`
    - _Requirements: 3.10, 2.3_

- [x] 5. Implement `PollingStep` component (`src/components/assets/PollingStep.tsx`)
  - [x] 5.1 Render title "Extracting Data...", centered circular spinner with sparkles icon, and descriptive text
    - _Requirements: 5.2, 5.3_
  - [x] 5.2 Render "EXTRACTION PROGRESS" card with three steps ("Analyzing Invoice", "Processing Photos", "Validating Serial Numbers"); animate step states (pending → in-progress → completed) via `useEffect` + `setInterval` cycling every 1500 ms; clear interval on unmount
    - _Requirements: 5.4, 5.5, 5.6, 5.9_
  - [ ]* 5.3 Write property test for polling interval cleanup on unmount (Property 5)
    - **Property 5: Polling Interval Cleanup**
    - **Validates: Requirements 5.9**
  - [x] 5.4 Wire `useScanJob(scanJobId)` — on `COMPLETED` call `onCancel()` then navigate to `/assets/new?scan_job_id=&upload_session_id=&ready=1` with `state: { extracted_fields }`; on `SCAN_FAILED` display `failure_reason` error inline; on network error display error and stop polling
    - _Requirements: 5.7, 5.8, 5.10_
  - [ ]* 5.5 Write property test for scan completion navigation (Property 6)
    - **Property 6: Scan Completion Navigation**
    - **Validates: Requirements 5.7**
  - [x] 5.6 Render "Cancel" button (outlined, destructive, full width) in footer; wire to `onCancel`
    - _Requirements: 5.11_

- [x] 6. Implement `UploadAssetModal` component (`src/components/assets/UploadAssetModal.tsx`)
  - Own `step: 'upload' | 'polling'`, `uploadSessionId`, and `scanJobId` state; reset all state when `open` transitions to `false`
  - Render Shadcn `Dialog`; conditionally render `UploadStep` or `PollingStep` based on `step`
  - Pass `onUploadComplete` to `UploadStep` to advance to polling step; pass `onCancel` (calls `onOpenChange(false)`) to both steps
  - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 7. Implement `ConfirmAssetForm` component (`src/components/assets/ConfirmAssetForm.tsx`)
  - [x] 7.1 Define `confirmSchema` Zod object at module scope; read `extracted_fields` from TanStack Router navigation state via `Route.useMatch()`; pre-fill the nine extractable fields from `extracted_fields.{key}.value`; leave `category`, `procurement_id`, `approved_budget`, `requestor` empty
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  - [x] 7.2 Render all form fields using `form.Field` + Shadcn inputs; apply `border-warning` class to inputs where `confidence < 0.8`; render `{Math.round(confidence * 100)}% confidence` label adjacent to each pre-filled field; render `Alternative: {alternative_value}` hint below field when `alternative_value` is non-empty
    - _Requirements: 6.5, 6.6, 6.7_
  - [ ]* 7.3 Write property test for confidence threshold styling (Property 7)
    - **Property 7: Confidence Threshold Styling**
    - **Validates: Requirements 6.5**
  - [ ]* 7.4 Write property test for extracted field rendering (Property 8)
    - **Property 8: Extracted Field Rendering**
    - **Validates: Requirements 6.6, 6.7**
  - [x] 7.5 Wire `useCreateAsset` mutation to form submit; include `scan_job_id` from URL search param in the POST body; disable submit button via `form.state.isSubmitting`; navigate to `/assets/new?asset_id={asset_id}` on success; display `ApiError.message` inline on error
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  - [ ]* 7.6 Write property test for confirm form submission integrity (Property 9)
    - **Property 9: Confirm Form Submission Integrity**
    - **Validates: Requirements 7.1**

- [x] 8. Checkpoint — ensure modal and form components compile and render correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement `/assets/new` route (`src/routes/_authenticated/assets.new.tsx`)
  - [x] 9.1 Define `searchSchema` Zod object at module scope (`upload_session_id`, `scan_job_id`, `ready`, `asset_id` all optional); attach to route via `validateSearch`; define `ASSET_NEW_SEO` const with `satisfies SeoPageInput`; attach `head` with noindex override
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 13.1, 13.4_
  - [x] 9.2 In the `Asset_Creation_Wizard` component body: if `asset_id` present render `SuccessStep`; if `scan_job_id` + `ready === 1` render `ConfirmAssetForm`; otherwise `throw redirect({ to: '/assets' })`
    - _Requirements: 1.1, 1.2, 1.3_
  - [ ]* 9.3 Write property test for step routing completeness (Property 1)
    - **Property 1: Step Routing Completeness**
    - **Validates: Requirements 1.1, 1.2, 1.3**
  - [x] 9.4 Implement inline `SuccessStep`: display "Asset {asset_id} created and pending management approval."; render "Create Another Asset" `<Link>` to `/assets` and "View Asset List" `<Link>` to `/assets` using `<Button asChild>`
    - _Requirements: 8.1, 8.2, 8.3_
  - [ ]* 9.5 Write property test for success step message containing asset ID (Property 14)
    - **Property 14: Success Step Message Contains Asset ID**
    - **Validates: Requirements 8.1**
  - [x] 9.6 Add `it-admin`-only `beforeLoad` guard; throw `redirect({ to: '/unauthorized' })` for other roles
    - _Requirements: 1.1_

- [x] 10. Implement `/assets/:asset_id/approve` route (`src/routes/_authenticated/assets.$asset_id.approve.tsx`)
  - [x] 10.1 Define `ASSET_APPROVE_SEO` const; attach `head` with noindex override; add `management`-only `beforeLoad` guard using `APPROVE_ALLOWED: UserRole[]` constant; throw `redirect({ to: '/unauthorized' })` for non-management roles
    - _Requirements: 10.1, 10.2, 13.3, 13.4_
  - [ ]* 10.2 Write property test for management role guard (Property 12)
    - **Property 12: Management Role Guard**
    - **Validates: Requirements 10.2**
  - [x] 10.3 Render `asset_id` prominently; render "Approve" and "Reject" buttons; on Approve click show optional remarks textarea; on Reject click show required rejection reason textarea; disable reject confirm button while textarea is empty or whitespace-only
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_
  - [ ]* 10.4 Write property test for rejection reason required (Property 13)
    - **Property 13: Rejection Reason Required**
    - **Validates: Requirements 11.5**
  - [x] 10.5 Wire `useApproveAsset(assetId)` to confirm actions; call with `{ action: 'APPROVE', remarks }` or `{ action: 'REJECT', rejection_reason }`; on success display new `status` value and render "Back to List" `<Link>` to `/assets`; display `ApiError.message` inline on error
    - _Requirements: 11.6, 11.7, 11.8, 11.9, 11.10_

- [x] 11. Replace mock implementation in `/assets` route (`src/routes/_authenticated/assets.tsx`)
  - [x] 11.1 Add `assetsSearchSchema` Zod object (`page`, `status`) to route `validateSearch`; update `ASSETS_SEO` description if needed; confirm `head` already uses noindex override pattern
    - _Requirements: 9.1, 9.5, 13.2, 13.4_
  - [x] 11.2 Replace mock `data` and `useState(1)` pagination with `useAssets()`; wire `currentPage`, `setCurrentPage`, `statusFilter`, `setStatusFilter` from the hook to the table and filter dropdown; replace mock columns with real `AssetItem` columns (Asset ID, Brand, Model, Serial Number, Status using `ASSET_STATUS_LABELS` + semantic badge classes, Assignment Date)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9_
  - [ ]* 11.3 Write property test for asset list pagination and filter params (Property 10)
    - **Property 10: Asset List Pagination and Filter Params**
    - **Validates: Requirements 9.1, 9.4, 9.6**
  - [x] 11.4 Add row click handler: when `status === 'ASSET_PENDING_APPROVAL'` navigate to `/assets/{asset_id}/approve` using `useNavigate`
    - _Requirements: 9.10_
  - [ ]* 11.5 Write property test for pending approval row navigation (Property 11)
    - **Property 11: Pending Approval Row Navigation**
    - **Validates: Requirements 9.10**
  - [x] 11.6 Add `open` / `setOpen` local state for `UploadAssetModal`; wire "Add New Asset" button to `setOpen(true)`; render `<UploadAssetModal open={open} onOpenChange={setOpen} />` at the bottom of the component
    - _Requirements: 2.1, 1.6_

- [x] 12. Final checkpoint — ensure all tests pass and routes are wired correctly
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Property tests use `fast-check` with a minimum of 100 iterations per run
- Each property test must include a comment tag: `// Feature: asset-creation-flow, Property N: <title>`
- Semantic status tokens (`badge-warning`, `border-warning`, `text-danger`, etc.) must be used for all status UI — never raw Tailwind color utilities
- Presigned URL PUT requests must use plain `fetch`, never `apiClient`, and must not include an `Authorization` header
- All `<Link>` navigation in JSX must use `<Button asChild><Link ...>` pattern — never `onClick={() => navigate(...)}`
- `routeTree.gen.ts` must never be manually edited; TanStack Router plugin regenerates it automatically when new route files are added
