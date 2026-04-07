# Implementation Plan: Asset Return Process

## Overview

Implement the full asset return workflow across the data layer, shared UI components, dialog components, new route pages, and integration into existing pages. Tasks are ordered by dependency: foundation first, then UI primitives, then dialogs, then routes, then integration.

## Tasks

- [x] 1. Extend query keys, types, and permissions foundation
  - [x] 1.1 Add `returns` namespace to `src/lib/query-keys.ts`
    - Add `returns.all()`, `returns.list(assetId, filters)`, `returns.detail(assetId, returnId)`, `returns.pendingReturns(filters)`, `returns.pendingSignatures(filters)` following the existing factory pattern
    - Import `ListReturnsFilter` from `#/lib/models/types` for the `list` key
    - _Requirements: 10.3_

  - [x] 1.2 Extend `src/lib/permissions.ts` with return permissions
    - Add `ReturnDetailContext` type and `ReturnDetailPermissions` type
    - Export `getReturnDetailPermissions(ctx)` returning `canUploadEvidence`, `canRenotifyEmployee`, `canSignAndComplete`, `canViewReturnsTab` boolean flags per the design spec
    - Extend `AssetDetailPermissions` with `showInitiateReturnButton: boolean`
    - Extend `getAssetDetailPermissions` to compute `showInitiateReturnButton` as `hasRole(role, ['it-admin']) && assetStatus === 'ASSIGNED'`
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

- [x] 2. Implement `src/hooks/use-returns.ts`
  - [x] 2.1 Create the query hooks: `useReturnDetail`, `useReturns`, `usePendingReturns`, `usePendingSignatures`
    - `useReturnDetail(assetId, returnId)` → `GET /assets/{assetId}/returns/{returnId}`, returns `GetReturnResponse`, `staleTime: 60_000`
    - `useReturns(assetId, filters, page, pageSize?)` → `GET /assets/{assetId}/returns` with query params, returns `ListReturnsResponse`, `staleTime: 60_000`
    - `usePendingReturns(page, pageSize?)` → `GET /assets/pending-returns`, returns `ListPendingReturnsResponse`, `staleTime: 60_000`
    - `usePendingSignatures(page, pageSize?)` → `GET /users/me/pending-signatures`, returns `ListPendingSignaturesResponse`, `staleTime: 60_000`
    - All use `queryKeys.returns.*` factory keys — no raw string arrays
    - _Requirements: 10.1, 10.8_

  - [x] 2.2 Create the mutation hooks: `useInitiateReturn`, `useGenerateReturnUploadUrls`, `useSubmitAdminEvidence`, `useGenerateReturnSignatureUploadUrl`, `useCompleteReturn`
    - `useInitiateReturn(assetId)` → `POST /assets/{assetId}/returns`, invalidates `queryKeys.assets.detail(assetId)`, `queryKeys.returns.list(assetId, {})`, `queryKeys.issues.pendingReturns({})` in `onSettled`
    - `useGenerateReturnUploadUrls(assetId, returnId)` → `POST /assets/{assetId}/returns/{returnId}/upload-urls`, no cache invalidation
    - `useSubmitAdminEvidence(assetId, returnId)` → `POST /assets/{assetId}/returns/{returnId}/submit-evidence` (empty body), invalidates `queryKeys.returns.detail(assetId, returnId)`, `queryKeys.returns.pendingSignatures({})` in `onSettled`
    - `useGenerateReturnSignatureUploadUrl(assetId, returnId)` → `POST /assets/{assetId}/returns/{returnId}/signature-upload-url`, no cache invalidation
    - `useCompleteReturn(assetId, returnId)` → `PUT /assets/{assetId}/returns/{returnId}/complete` with `{ user_signature_s3_key }`, invalidates `queryKeys.assets.detail(assetId)`, `queryKeys.returns.detail(assetId, returnId)`, `queryKeys.returns.pendingSignatures({})` in `onSettled`
    - All mutations use `mutationKey` arrays and `onSettled` for invalidation
    - _Requirements: 10.2, 10.4, 10.5, 10.6, 10.7_

- [ ] 3. Checkpoint — Ensure data layer compiles cleanly
  - Ensure all types resolve, query keys are consistent, and permissions functions are exported correctly. Ask the user if questions arise.

- [x] 4. Implement shared badge and display components in `src/components/returns/`
  - [x] 4.1 Create `ReturnConditionBadge.tsx`
    - Props: `{ condition: ReturnCondition | undefined }`
    - Variants: `success` (GOOD), `warning` (MINOR_DAMAGE, MINOR_DAMAGE_REPAIR_REQUIRED), `danger` (MAJOR_DAMAGE); uses `ReturnConditionLabels`
    - _Requirements: 8.2_

  - [x] 4.2 Create `ResetStatusBadge.tsx`
    - Props: `{ status: ResetStatus | undefined }`
    - Variants: `success` (COMPLETE), `danger` (INCOMPLETE); uses `ResetStatusLabels`
    - _Requirements: 8.2_

  - [x] 4.3 Create `ReturnStatusBadge.tsx`
    - Props: `{ status: AssetStatus | undefined }` — `undefined`/null renders `warning` "Pending"
    - Variants per design: `warning` (null/undefined, DAMAGED, REPAIR_REQUIRED), `success` (IN_STOCK), `danger` (DISPOSAL_REVIEW); uses `AssetStatusLabels`
    - _Requirements: 8.2_

  - [x] 4.4 Create `ReturnTriggerDisplay.tsx`
    - Props: `{ trigger: ReturnTrigger }`
    - Read-only single bordered row with trigger icon + label from `ReturnTriggerLabels`; not interactive
    - _Requirements: 6.1_

- [x] 5. Implement shared structural components in `src/components/returns/`
  - [x] 5.1 Create `HandoverTimestampPill.tsx`
    - Props: `{ label: string; timestamp: string }`
    - Renders bordered pill row: label (uppercase, muted) on left, `formatDate(timestamp)` + Clock icon on right
    - Import `formatDate` from `#/lib/utils`
    - _Requirements: 2.1_

  - [x] 5.2 Create `ReturnTriggerSelector.tsx`
    - Props: `{ value: ReturnTrigger | ''; onChange: (value: ReturnTrigger) => void; disabled?: boolean }`
    - 2-column grid of toggle buttons (RESIGNATION, REPLACEMENT, TRANSFER, IT_RECALL) + full-width UPGRADE button
    - Selected state: `border-primary bg-primary/10 text-primary`; unselected: `border-border text-muted-foreground hover:border-primary/50`
    - Each button: `border rounded-lg p-3 flex flex-col items-center gap-1.5 text-sm cursor-pointer transition-colors`
    - Icons: `UserMinus`, `RefreshCw`, `ArrowRightLeft`, `MonitorX`, `ArrowUpCircle` from lucide-react
    - Labels from `ReturnTriggerLabels`
    - _Requirements: 1.2_

  - [x] 5.3 Create `AssetDetailsCard.tsx`
    - Props: `{ model: string | undefined; serialNumber: string | undefined; mode: 'edit' | 'readonly'; conditionValue?: ReturnCondition | ''; onConditionChange?: (value: ReturnCondition) => void; conditionInvalid?: boolean }`
    - Styled with `bg-info/10 border border-info/20 rounded-lg p-4`; Database icon (blue) + "Asset Details" label
    - Edit mode: condition row renders a Shadcn `<Select>` with `ReturnConditionLabels` options; readonly mode: plain text
    - _Requirements: 1.2, 6.1_

  - [x] 5.4 Create `EvidencePhotoGrid.tsx`
    - Props: `{ mode: 'upload' | 'readonly'; files?: File[]; onFilesChange?: (files: File[]) => void; photoUrls?: string[] }`
    - Upload mode: 3-column grid, first cell is dashed-border upload tile (Camera icon + "Upload", opens file picker `accept="image/jpeg,image/png"`, max 10 files), remaining cells show `<img>` previews with remove button overlay
    - Readonly mode: all cells are `<a>` thumbnails linking to full URL
    - _Requirements: 2.3_

  - [x] 5.5 Create `SignatureCard.tsx`
    - Props: `{ label: string; idLabel?: string; onClear: () => void; sigRef: React.RefObject<SignatureCanvas>; disabled?: boolean }`
    - Bordered card: header row with label (blue, uppercase, small) + "Clear" ghost button; body with `react-signature-canvas` filling `h-[200px]`; optional `idLabel` in bottom-right corner
    - Uses `react-signature-canvas` directly (draw-only, no upload tab)
    - _Requirements: 2.6, 6.1_

- [x] 6. Implement `ReturnsTab` component
  - [x] 6.1 Create `src/components/returns/ReturnsTab.tsx`
    - Props: `{ assetId: string; search: { ret_page?: number; ret_trigger?: ReturnTrigger; ret_condition?: ReturnCondition }; onSearchChange: (updates: Record<string, unknown>) => void }`
    - Define `createColumnHelper<ReturnListItem>()` at module scope
    - Columns: Return Trigger (`ReturnTriggerLabels[row.return_trigger]`), Condition (`<ReturnConditionBadge>`), Initiated By, Initiated At (`formatDate`), Status (`<ReturnStatusBadge status={row.resolved_status}>`), Completed At (`formatDate || '—'`), Actions (eye icon → `/assets/${assetId}/returns/${row.return_id}`)
    - Toolbar: Filters button (opens filter dialog) + Clear all; filter dialog has Return Trigger Select + Condition Assessment Select following the filter-ui protocol
    - Uses `useReturns(assetId, filters, page)` hook
    - Empty state: "No returns recorded for this asset."
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 7. Implement `InitiateReturnDialog` component
  - [x] 7.1 Create `src/components/returns/InitiateReturnDialog.tsx`
    - Props: `{ open: boolean; onOpenChange: (open: boolean) => void; assetId: string; asset: { model?: string; serial_number?: string }; onSuccess: (returnId: string) => void }`
    - `DialogContent` sized `max-w-4xl`, two-column layout (`grid-cols-2 gap-6`), scrollable body with `-mx-1 px-1` pattern, pinned `DialogFooter`
    - Left column: "PURPOSE OF RETURN" label + `<ReturnTriggerSelector>` + `<AssetDetailsCard mode="readonly">` (asset details only, no condition field here)
    - Right column: `<HandoverTimestampPill>` (timestamp captured via `useState(() => new Date().toISOString())`) + placeholder text for photos and signature ("will be captured in the next step")
    - TanStack Form with Zod schema: `{ return_trigger: z.enum([...]) }` — `onSubmit` validator
    - Footer: [Cancel] outline + [Next: Upload Evidence] primary with ShieldCheck icon
    - On submit: calls `useInitiateReturn(assetId).mutate({ return_trigger })`, on success shows `toast.success('Return initiated. Asset is now pending return.')`, calls `onSuccess(returnId)`
    - Error handling: 409 "Asset is not in ASSIGNED status" → `toast.error()`; 404 → `toast.error()`; 400/409 "Device factory reset..." → inline `alert-danger` below form
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.12_

- [x] 8. Implement `UploadEvidenceDialog` component
  - [x] 8.1 Create `src/components/returns/UploadEvidenceDialog.tsx`
    - Props: `{ open: boolean; onOpenChange: (open: boolean) => void; assetId: string; returnId: string; asset: { model?: string; serial_number?: string }; initiatedAt: string; onSuccess: () => void }`
    - `DialogContent` sized `max-w-4xl`, two-column layout, scrollable body, pinned footer
    - Left column: read-only trigger display (fetch from `useReturnDetail` or pass as prop) + `<AssetDetailsCard mode="edit">` bound to `condition_assessment` + Reset Status radio group + Remarks textarea
    - Right column: `<HandoverTimestampPill>` + `<EvidencePhotoGrid mode="upload">` + `<SignatureCard label="ADMIN SIGNATURE" idLabel={...} sigRef={sigRef}>`
    - TanStack Form with Zod schema: `{ condition_assessment, reset_status, remarks }` — `onSubmit` validator; use `<Field>`, `<FieldLabel>`, `<FieldError>` for all fields
    - Internal upload state machine: `'form' | 'uploading' | 'submitting' | 'done'`
    - On submit: validate form → export signature canvas as PNG blob → call `useGenerateReturnUploadUrls` with photo files + signature manifest → `Promise.allSettled` S3 PUTs → check for 403 (expired URL toast) → call `useSubmitAdminEvidence` → `toast.success('Evidence submitted. Employee has been notified to provide their signature.')` → call `onSuccess()`
    - Error handling per requirements 2.8, 2.9, 2.10, 2.11
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12, 2.13, 3.1, 3.2_

- [x] 9. Implement `EmployeeSignatureDialog` component
  - [x] 9.1 Create `src/components/returns/EmployeeSignatureDialog.tsx`
    - Props: `{ open: boolean; onOpenChange: (open: boolean) => void; assetId: string; returnId: string; returnData: GetReturnResponse; employeeName: string; onSuccess: () => void }`
    - `DialogContent` sized `max-w-4xl`, two-column layout, scrollable body, pinned footer
    - Left column (read-only): `<ReturnTriggerDisplay>` + `<AssetDetailsCard mode="readonly">` + read-only remarks block (`<p className="text-sm bg-muted/30 rounded-lg p-3 min-h-[80px]">`)
    - Right column: `<HandoverTimestampPill label="RETURN TIMESTAMP">` + `<EvidencePhotoGrid mode="readonly" photoUrls={returnData.return_photo_urls}>` + `<SignatureCard label={\`USER SIGNATURE (\${employeeName.toUpperCase()})\`}>`
    - Footer: [Cancel] outline + [Complete Return] primary with ShieldCheck icon
    - On submit: export canvas as PNG blob (show `toast.error` if empty) → call `useGenerateReturnSignatureUploadUrl` → S3 PUT → on 403 show `toast.error` → call `useCompleteReturn({ user_signature_s3_key })` → `toast.success('Return completed successfully.')` → call `onSuccess()` → navigate to `/`
    - Error handling per requirements 6.5, 6.6, 6.7, 7.4, 7.5, 7.6
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 7.1, 7.2, 7.3_

- [x] 10. Checkpoint — Ensure all components compile and dialog flows are wired
  - Ensure all return components in `src/components/returns/` compile without type errors. Ask the user if questions arise.

- [ ] 11. Create `assets.$asset_id.returns.$return_id.tsx` route
  - [x] 11.1 Create `src/routes/_authenticated/assets.$asset_id.returns.$return_id.tsx`
    - `createFileRoute('/_authenticated/assets/$asset_id/returns/$return_id')` with `as any` cast
    - Allowed roles: `['it-admin', 'employee']`; `beforeLoad` uses `hasRole` with context cast pattern
    - SEO constant `RETURN_DETAIL_SEO` at module scope with `satisfies SeoPageInput`; `head` uses `getBaseMeta()` + `noindex, nofollow` + `getPageMeta` + `getCanonicalLink`
    - No `validateSearch` needed
    - Component `ReturnDetailPage`: calls `useReturnDetail(asset_id, return_id)`, `useCurrentUserRole()`, `useCurrentUserId()`
    - Two-column layout (`lg:grid-cols-3`, left `lg:col-span-2`): breadcrumb (Assets → asset_id → Return Detail), loading skeleton, `alert-danger` for 403/404 errors
    - Left column cards: Return Info, Device Info, Condition Assessment (`<ReturnConditionBadge>`, `<ResetStatusBadge>`, remarks), Admin Evidence (`<EvidencePhotoGrid mode="readonly">` + admin signature img or "Not yet uploaded"), Employee Evidence (user signature img or "Pending employee signature"), Completion card (conditional on `completed_at`)
    - Right sidebar: Status card (`<Badge>` for `asset_status`), Actions card with conditional buttons from `getReturnDetailPermissions`: "Upload Evidence" → opens `<UploadEvidenceDialog>`, "Re-notify Employee" → calls `useSubmitAdminEvidence` directly with `toast.success/error`, "Sign & Complete Return" → opens `<EmployeeSignatureDialog>`
    - All dates via `formatDate`; all status badges use semantic variants
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11, 3.3_

- [ ] 12. Create `pending-returns.tsx` route
  - [x] 12.1 Create `src/routes/_authenticated/pending-returns.tsx`
    - `createFileRoute('/_authenticated/pending-returns')`
    - Allowed roles: `['it-admin']`; `beforeLoad` uses `hasRole`
    - `validateSearch` with Zod schema: `{ page: z.coerce.number().min(1).optional() }`
    - SEO constant `PENDING_RETURNS_SEO` at module scope; `head` uses authenticated pattern
    - Component `PendingReturnsPage`: calls `usePendingReturns(page, PAGE_SIZE)`
    - Define `createColumnHelper<PendingReturnItem>()` at module scope
    - Columns: Asset ID (link in actions column), Brand/Model combined, Serial Number (`?? 'N/A'`), Assigned To, Replacement Approved At (`formatDate`), Replacement Justification (truncated), Management Remarks (truncated), Actions: eye icon → `/assets/${row.asset_id}` + dropdown with "Initiate Return" item → `navigate({ to: '/assets/$asset_id', params: { asset_id }, search: { initiate_return: true } })`
    - Empty state: "No assets pending return."
    - Pagination via `page` search param
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

- [ ] 13. Create `pending-signatures.tsx` route
  - [x] 13.1 Create `src/routes/_authenticated/pending-signatures.tsx`
    - `createFileRoute('/_authenticated/pending-signatures')`
    - Allowed roles: `['employee']`; `beforeLoad` uses `hasRole`
    - `validateSearch` with Zod schema: `{ page: z.coerce.number().min(1).optional() }`
    - SEO constant `PENDING_SIGNATURES_SEO` at module scope; `head` uses authenticated pattern
    - Component `PendingSignaturesPage`: calls `usePendingSignatures(page, PAGE_SIZE)`
    - Define `createColumnHelper<PendingSignatureItem>()` at module scope
    - Columns: Type (`<Badge variant={row.document_type === 'return' ? 'info' : 'default'}>` "Return"/"Handover"), Asset ID (plain text), Return Trigger (`ReturnTriggerLabels[row.return_trigger] ?? '—'`), Initiated At (`formatDate || '—'`), Actions: eye icon → return type navigates to `/assets/${row.asset_id}/returns/${row.record_id}`, handover type navigates to `/assets/${row.asset_id}`
    - Empty state: "No pending signatures."
    - Pagination via `page` search param
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

- [ ] 14. Integrate return flow into `assets.$asset_id.tsx`
  - [x] 14.1 Extend `assetDetailSearchSchema` in `assets.$asset_id.tsx`
    - Add `ret_page: z.coerce.number().min(1).optional()`
    - Add `ret_trigger: z.enum(['RESIGNATION','REPLACEMENT','TRANSFER','IT_RECALL','UPGRADE'] as const).optional()`
    - Add `ret_condition: z.enum(['GOOD','MINOR_DAMAGE','MINOR_DAMAGE_REPAIR_REQUIRED','MAJOR_DAMAGE'] as const).optional()`
    - Add `initiate_return: z.boolean().optional()`
    - Add `isReturnDetailActive` matchRoute check (same pattern as `isIssueDetailActive`) so the returns child route renders via `<Outlet />`
    - _Requirements: 8.1, 9.3_

  - [x] 14.2 Add IT Admin return flow state machine and "Initiate Return" button to `assets.$asset_id.tsx`
    - Add local state: `type ReturnFlowState = { step: 'idle' } | { step: 'initiate' } | { step: 'upload-evidence'; returnId: string; initiatedAt: string } | { step: 'done' }`
    - Add `useEffect` that reads `search.initiate_return` and sets state to `{ step: 'initiate' }` on mount (for deep-link from Pending Returns page)
    - Destructure `showInitiateReturnButton` from `getAssetDetailPermissions` result
    - Add "Initiate Return" button to `<QuickActionsCard>` (extend `QuickActionsCardProps` with `showInitiateReturn?: boolean` and `onInitiateReturn?: () => void`)
    - Render `<InitiateReturnDialog>` and `<UploadEvidenceDialog>` controlled by the state machine
    - _Requirements: 1.1, 1.5, 1.6, 9.3_

  - [x] 14.3 Add Returns tab to the asset detail tabs section
    - Import `<ReturnsTab>` and add it to the `<Tabs>` component when `canViewReturnsTab` is true (from `getReturnDetailPermissions` or directly from `getAssetDetailPermissions`)
    - Add `'returns'` to the `tab` enum in `assetDetailSearchSchema`
    - Wire `ret_page`, `ret_trigger`, `ret_condition` search params to `<ReturnsTab>` via `onSearchChange` handler (same prefixed pattern as `sr_` params)
    - _Requirements: 8.1, 8.3_

- [x] 15. Extend `QuickActionsCard` to support Initiate Return button
  - Add `showInitiateReturn?: boolean` and `onInitiateReturn?: () => void` props to `QuickActionsCardProps` in `src/components/assets/detail/QuickActionsCard.tsx`
  - Render "Initiate Return" button (RotateCcw icon) when `showInitiateReturn` is true
  - _Requirements: 1.1_

- [ ] 16. Add navigation items for new routes
  - [x] 16.1 Add "Pending Returns" nav item to `src/components/general/Header.tsx` (or wherever the main nav is rendered)
    - Conditionally render using `hasRole(role, ['it-admin'])` — link to `/pending-returns`
    - _Requirements: 9.6_

  - [x] 16.2 Add "Pending Signatures" nav item to the main nav
    - Conditionally render using `hasRole(role, ['employee'])` — link to `/pending-signatures`
    - _Requirements: 5.7_

- [x] 17. Final checkpoint — Ensure all tests pass
  - Ensure all components compile, routes are accessible, and the full return flow (initiate → upload evidence → submit → employee sign → complete) is wired end-to-end. Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- The IT Admin flow is a state machine: `idle → initiate → upload-evidence → done`
- `UploadEvidenceDialog` handles condition/reset/remarks fields (not `InitiateReturnDialog`) — `InitiateReturnRequest` only has `return_trigger`
- `CompleteReturnRequest` fields (`serial_number`, `model`, `condition_assessment`, `remarks`, `reset_status`) are submitted by the IT Admin via the Upload Evidence step, not the employee
- The employee's `useCompleteReturn` call only sends `{ user_signature_s3_key }`
- All S3 upload flows must check for 403 (expired presigned URL) separately from other failures
- `routeTree.gen.ts` must NOT be manually edited — it is auto-generated when route files change
