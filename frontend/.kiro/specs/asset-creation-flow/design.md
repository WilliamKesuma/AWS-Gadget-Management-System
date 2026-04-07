# Design Document: Asset Creation Flow

## Overview

The Asset Creation Flow is a multi-step wizard that allows IT Admins to upload invoice and gadget photo files, wait for AI-powered field extraction, review and confirm the extracted data, and submit the asset for management approval. The flow is split between a modal dialog (Steps 1–2) and full-page routes (Steps 3–4), with a separate Asset List page and a Management-only Approve/Reject page.

The design follows the existing project conventions: TanStack Router for routing with Zod-validated search params, TanStack Query for all server state, TanStack Form + `@tanstack/zod-form-adapter` for forms, and Shadcn UI components throughout.

### Key Design Decisions

1. **Modal vs. full-page split**: Steps 1–2 (upload + polling) live inside a Dialog on `/assets` to avoid polluting the URL with transient upload state. Steps 3–4 are full pages because they are bookmarkable and refreshable.
2. **URL as source of truth for full-page steps**: The `Asset_Creation_Wizard` at `/assets/new` reads search params to determine which step to render — no component-level step state needed.
3. **Router navigation state for extracted fields**: `extracted_fields` is passed via TanStack Router navigation state (not URL params) to avoid exposing potentially large JSON in the URL. Graceful degradation to empty form on direct navigation.
4. **Presigned URL uploads bypass `apiClient`**: S3 PUT requests use plain `fetch` with no Authorization header, matching AWS presigned URL requirements.
5. **Polling via `refetchInterval` function**: `useScanJob` uses `(query) => query.state.data?.status === 'PROCESSING' ? 3000 : false` so TanStack Query automatically stops polling when the job reaches a terminal state.
6. **Animated progress is purely cosmetic**: A `useEffect` + `setInterval` cycles the 3-step animation independently of actual API state. Navigation is triggered solely by query data.

---

## Architecture

```
/assets                          Asset_List_Page
  └── <UploadAssetModal>         Dialog (steps 1–2, local state)
        ├── <UploadStep>         File selection + S3 upload
        └── <PollingStep>        Scan job polling + animation

/assets/new                      Asset_Creation_Wizard (route)
  ├── ?scan_job_id=&ready=1  →   <ConfirmAssetForm>   (Step 3)
  └── ?asset_id=             →   <SuccessStep>        (Step 4)

/assets/:asset_id/approve        ApprovePage (management only)
```

### Component Hierarchy

```
AssetsPage (assets.tsx)
├── Header + "Add New Asset" button
├── Status filter dropdown
├── DataTable<AssetItem>
│   └── Row click → /assets/:id/approve (ASSET_PENDING_APPROVAL only)
└── UploadAssetModal (Dialog)
    ├── step === 'upload'   → UploadStep
    │   ├── DragDropZone (invoice: PDF/image, max 1)
    │   ├── DragDropZone (photos: image, 1–5)
    │   └── "UPLOADED FILES" list with trash icons
    └── step === 'polling'  → PollingStep
        └── Spinner + "EXTRACTION PROGRESS" animated card

AssetCreationWizard (assets.new.tsx)
├── asset_id present        → SuccessStep
├── scan_job_id + ready=1   → ConfirmAssetForm
└── otherwise               → redirect('/assets')

ApprovePage (assets.$asset_id.approve.tsx)
├── beforeLoad: management-only guard
├── Asset ID display
├── Approve action (optional remarks textarea)
└── Reject action (required rejection_reason textarea)
```

---

## Components and Interfaces

### New Files

```
src/
  hooks/
    use-assets.ts              useAssets(), useUploadAsset(), useScanJob(), useCreateAsset(), useApproveAsset()
  components/
    assets/
      UploadAssetModal.tsx     Dialog wrapper; owns 'upload' | 'polling' step state
      UploadStep.tsx           Drag-drop zones + file list + client-side validation
      PollingStep.tsx          Spinner + animated 3-step progress card
      ConfirmAssetForm.tsx     TanStack Form pre-filled from extracted_fields
  routes/
    _authenticated/
      assets.tsx               Replace mock with real API + UploadAssetModal
      assets.new.tsx           /assets/new — Confirm + Success steps
      assets.$asset_id.approve.tsx  /assets/:asset_id/approve — management only
  lib/
    query-keys.ts              Add assets.list() and assets.scanJob() keys
    models/
      labels.ts                Add ASSET_STATUS_LABELS
```

### Component Props

```ts
// UploadAssetModal
interface UploadAssetModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

// UploadStep
interface UploadStepProps {
  onUploadComplete: (uploadSessionId: string, scanJobId: string) => void
  onCancel: () => void
}

// PollingStep
interface PollingStepProps {
  scanJobId: string
  uploadSessionId: string
  onCancel: () => void
}

// ConfirmAssetForm
interface ConfirmAssetFormProps {
  scanJobId: string
  uploadSessionId: string
  extractedFields: Record<string, ExtractedFieldValue> | undefined
}
```

---

## Data Models

### Query Key Additions (`src/lib/query-keys.ts`)

```ts
assets: {
  all: () => ['assets'] as const,
  list: (params: { page: number; page_size: number; status?: AssetStatus }) =>
    [...queryKeys.assets.all(), 'list', params] as const,
  scanJob: (scanJobId: string) =>
    [...queryKeys.assets.all(), 'scan-job', scanJobId] as const,
},
```

### Asset Status Labels (`src/lib/models/labels.ts`)

```ts
export const ASSET_STATUS_LABELS: Record<AssetStatus, string> = {
  IN_STOCK: 'In Stock',
  ASSIGNED: 'Assigned',
  ASSET_PENDING_APPROVAL: 'Pending Approval',
  ASSET_REJECTED: 'Rejected',
  DISPOSAL_REVIEW: 'Disposal Review',
  DISPOSAL_PENDING: 'Disposal Pending',
  DISPOSAL_APPROVED: 'Disposal Approved',
  DISPOSAL_REJECTED: 'Disposal Rejected',
  DISPOSED: 'Disposed',
  RETURN_PENDING: 'Return Pending',
  DAMAGED: 'Damaged',
  REPAIR_REQUIRED: 'Repair Required',
  UNDER_REPAIR: 'Under Repair',
}
```

### Confirm Step Zod Schema (module scope in `ConfirmAssetForm.tsx`)

```ts
const confirmSchema = z.object({
  category: z.enum(['LAPTOP', 'MOBILE_PHONE', 'TABLET', 'OTHERS']),
  procurement_id: z.string().min(1),
  approved_budget: z.number().positive(),
  requestor: z.string().min(1),
  invoice_number: z.string().min(1),
  vendor: z.string().min(1),
  purchase_date: z.string().min(1),
  brand: z.string().min(1),
  model_name: z.string().min(1),
  cost: z.number().positive(),
  serial_number: z.string().optional(),
  product_description: z.string().optional(),
  payment_method: z.string().optional(),
})
```

### Search Param Schema (`assets.new.tsx`)

```ts
const searchSchema = z.object({
  upload_session_id: z.string().optional(),
  scan_job_id: z.string().optional(),
  ready: z.coerce.number().optional(),
  asset_id: z.string().optional(),
})
```

Step detection (in component body):
- `asset_id` present → render `SuccessStep`
- `scan_job_id` + `ready === 1` → render `ConfirmAssetForm`
- Otherwise → `throw redirect({ to: '/assets' })`

### Asset List Search Param Schema (`assets.tsx`)

```ts
const assetsSearchSchema = z.object({
  page: z.coerce.number().min(1).default(1),
  status: z.enum([...AssetStatuses]).optional(),
})
```

---

## API Integration

### Endpoints

| Method | Path | Request | Response |
|--------|------|---------|----------|
| `POST` | `/assets/uploads` | `GenerateUploadUrlsRequest` | `GenerateUploadUrlsResponse` |
| `PUT` | `{presigned_url}` | File binary | 200 OK (S3 direct, no auth) |
| `GET` | `/assets/scan/{scan_job_id}` | — | `GetScanResultsResponse` |
| `POST` | `/assets` | `CreateAssetRequest` | `CreateAssetResponse` |
| `GET` | `/assets` | `?page&page_size&status` | `ListAssetsResponse` |
| `PUT` | `/assets/{asset_id}/approve` | `ApproveAssetRequest` | `ApproveAssetResponse` |

### Hook Implementations

**`useUploadAsset` (`use-upload-asset.ts`)**

```ts
interface UploadAssetInput {
  invoiceFile: File
  photoFiles: File[]
}

export function useUploadAsset() {
  return useMutation({
    mutationFn: async ({ invoiceFile, photoFiles }: UploadAssetInput) => {
      const files: FileManifestItem[] = [
        { name: invoiceFile.name, content_type: invoiceFile.type, type: 'invoice' },
        ...photoFiles.map(f => ({ name: f.name, content_type: f.type, type: 'gadget_photo' as const })),
      ]
      const response = await apiClient<GenerateUploadUrlsResponse>('/assets/uploads', {
        method: 'POST',
        body: JSON.stringify({ files }),
      })
      const allFiles = [invoiceFile, ...photoFiles]
      await Promise.all(
        response.urls.map((urlItem, i) =>
          fetch(urlItem.presigned_url, {
            method: 'PUT',
            body: allFiles[i],
            headers: { 'Content-Type': allFiles[i].type },
            // No Authorization header — presigned URLs are self-authenticating
          }).then(res => {
            if (!res.ok) throw new Error(`S3 upload failed for ${allFiles[i].name}: ${res.status}`)
          })
        )
      )
      return { upload_session_id: response.upload_session_id, scan_job_id: response.scan_job_id }
    },
  })
}
```

**`useScanJob` (`use-scan-job.ts`)**

```ts
export function useScanJob(scanJobId: string | null) {
  return useQuery({
    queryKey: queryKeys.assets.scanJob(scanJobId ?? ''),
    queryFn: () => apiClient<GetScanResultsResponse>(`/assets/scan/${scanJobId}`),
    enabled: !!scanJobId,
    // Stops polling automatically when status leaves PROCESSING
    refetchInterval: (query) =>
      query.state.data?.status === 'PROCESSING' ? 3000 : false,
  })
}
```

**`useAssets` (`use-assets.ts`)**

```ts
export function useAssets(pageSize = 10) {
  const [currentPage, setCurrentPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<AssetStatus | 'all'>('all')

  const handleStatusFilterChange = (value: AssetStatus | 'all') => {
    setStatusFilter(value)
    setCurrentPage(1) // reset page on filter change
  }

  const params = {
    page: currentPage,
    page_size: pageSize,
    status: statusFilter === 'all' ? undefined : statusFilter,
  }

  const listQuery = useQuery({
    queryKey: queryKeys.assets.list(params),
    queryFn: () => {
      const qp = new URLSearchParams({ page: String(params.page), page_size: String(params.page_size) })
      if (params.status) qp.set('status', params.status)
      return apiClient<ListAssetsResponse>(`/assets?${qp}`)
    },
    staleTime: 60 * 1000,
  })

  return { ...listQuery, currentPage, setCurrentPage, statusFilter, setStatusFilter: handleStatusFilterChange, pageSize }
}
```

**`useApproveAsset` (`use-assets.ts`)**

```ts
export function useApproveAsset(assetId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['assets', 'approve', assetId],
    mutationFn: (data: ApproveAssetRequest) =>
      apiClient<ApproveAssetResponse>(`/assets/${assetId}/approve`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.assets.all() })
    },
  })
}
```

**`useCreateAsset` (`use-create-asset.ts`)**

```ts
export function useCreateAsset() {
  return useMutation({
    mutationFn: (data: CreateAssetRequest) =>
      apiClient<CreateAssetResponse>('/assets', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  })
}
```

---

## State Management

### Upload Modal State (`UploadAssetModal`)

`UploadAssetModal` owns all transient upload state:

```ts
const [step, setStep] = useState<'upload' | 'polling'>('upload')
const [uploadSessionId, setUploadSessionId] = useState<string | null>(null)
const [scanJobId, setScanJobId] = useState<string | null>(null)
```

Transitions:
- `UploadStep.onUploadComplete(id, jobId)` → set both IDs, `setStep('polling')`
- X button / Cancel → `onOpenChange(false)`, reset state on close
- Scan `COMPLETED` → close modal, navigate to Confirm_Step URL with router state
- Scan `SCAN_FAILED` → stay on polling step, show error (no step change)

State is reset when the Dialog closes via `onOpenChange`. This prevents stale state if the user reopens the modal.

### Animated Progress State (`PollingStep`)

The 3-step animation runs independently of API state via a `useEffect` + `setInterval`. The actual navigation is triggered by `useScanJob` data:

```ts
type ProgressState = 'pending' | 'in-progress' | 'completed'
const [stepStates, setStepStates] = useState<ProgressState[]>(['in-progress', 'pending', 'pending'])

useEffect(() => {
  const interval = setInterval(() => {
    setStepStates(prev => /* advance one step at a time, cycle back */)
  }, 1500)
  return () => clearInterval(interval) // always cleared on unmount
}, [])

// Navigation driven by query data, not animation
useEffect(() => {
  if (scanResult?.status === 'COMPLETED') {
    onCancel() // close modal
    navigate({ to: '/assets/new', search: { scan_job_id: scanJobId, upload_session_id: uploadSessionId, ready: 1 },
      state: { extracted_fields: scanResult.extracted_fields } })
  }
}, [scanResult?.status])
```

### Confirm Step — Extracted Fields

`ConfirmAssetForm` reads router navigation state via `Route.useMatch()`:

```ts
const match = Route.useMatch()
const extractedFields = (match.state as any)?.extracted_fields as
  Record<string, ExtractedFieldValue> | undefined
```

If `extractedFields` is undefined (direct navigation), the form renders with empty string defaults — graceful degradation, no crash.

Field pre-fill mapping:

| Form field | `extracted_fields` key |
|-----------|----------------------|
| `invoice_number` | `invoice_number` |
| `vendor` | `vendor` |
| `purchase_date` | `purchase_date` |
| `brand` | `brand` |
| `model_name` | `model_name` |
| `cost` | `cost` (parsed to number) |
| `serial_number` | `serial_number` |
| `product_description` | `product_description` |
| `payment_method` | `payment_method` |

Fields `category`, `procurement_id`, `approved_budget`, and `requestor` are never pre-filled.

Confidence display logic per field:

```ts
const confidence = extractedFields?.[fieldName]?.confidence
const isLowConfidence = confidence !== undefined && confidence < 0.8
// Apply to input: className={isLowConfidence ? 'border-warning' : ''}
// Label: {confidence !== undefined && `${Math.round(confidence * 100)}% confidence`}
// Hint: {extractedFields?.[fieldName]?.alternative_value && `Alternative: ${...}`}
```

---

## Routing Design

### Route Files

| File | Route | Guard |
|------|-------|-------|
| `assets.tsx` | `/assets` | `it-admin`, `management`, `employee` |
| `assets.new.tsx` | `/assets/new` | `it-admin` only |
| `assets.$asset_id.approve.tsx` | `/assets/:asset_id/approve` | `management` only |

### Approve Page Route Guard

```ts
const APPROVE_ALLOWED: UserRole[] = ['management']

export const Route = createFileRoute('/_authenticated/assets/$asset_id/approve')({
  beforeLoad: ({ context }) => {
    if (!context.userRole || !APPROVE_ALLOWED.includes(context.userRole)) {
      throw redirect({ to: '/unauthorized' })
    }
  },
  // ...
})
```

### SEO Constants

```ts
// assets.tsx
const ASSETS_SEO = {
  title: 'Asset Inventory',
  description: 'Track, assign, and manage organization-wide hardware assets, monitor lifecycle status, and oversee equipment availability.',
  path: '/assets',
} satisfies SeoPageInput

// assets.new.tsx
const ASSET_NEW_SEO = {
  title: 'Create Asset',
  description: 'Review AI-extracted asset details, confirm field values, and submit the asset for management approval.',
  path: '/assets/new',
} satisfies SeoPageInput

// assets.$asset_id.approve.tsx
const ASSET_APPROVE_SEO = {
  title: 'Approve Asset',
  description: 'Review and approve or reject a pending asset submission as a management user.',
  path: '/assets/approve',
} satisfies SeoPageInput
```

All three routes use the authenticated `head` pattern (noindex override):

```ts
head: () => ({
  meta: [
    ...getBaseMeta(),
    { name: 'robots', content: 'noindex, nofollow' },
    ...getPageMeta(ROUTE_SEO),
  ],
  links: [getCanonicalLink(ROUTE_SEO.path)],
}),
```

---

## Data Flow

### Upload Flow (Steps 1–2)

```
User clicks "Add New Asset"
  → AssetsPage: setModalOpen(true)
  → UploadAssetModal renders with step = 'upload'

User selects files + clicks "Upload & Scan"
  → UploadStep validates files client-side (count, MIME type)
  → useUploadAsset.mutate({ invoiceFile, photoFiles })
      → POST /assets/uploads via apiClient (with auth header)
      → parallel fetch PUT to each presigned_url (no auth header)
  → onSuccess: UploadStep calls onUploadComplete(uploadSessionId, scanJobId)
  → UploadAssetModal: setStep('polling'), store IDs in state

PollingStep mounts
  → useScanJob(scanJobId) starts polling GET /assets/scan/{scanJobId} every 3s
  → Animation setInterval cycles step states independently

  On COMPLETED:
    → refetchInterval returns false (polling stops)
    → navigate to /assets/new?scan_job_id=X&upload_session_id=Y&ready=1
      with state: { extracted_fields }
    → UploadAssetModal closes

  On SCAN_FAILED:
    → refetchInterval returns false (polling stops)
    → PollingStep displays failure_reason error; modal stays open

  On network error:
    → PollingStep displays error; polling stops
```

### Confirm Flow (Step 3)

```
User arrives at /assets/new?scan_job_id=X&upload_session_id=Y&ready=1
  → Asset_Creation_Wizard detects Confirm_Step (scan_job_id + ready === 1)
  → ConfirmAssetForm reads extracted_fields from router navigation state
  → Form pre-fills fields; fields with confidence < 0.8 get border-warning class
  → Confidence % labels and alternative_value hints rendered per field

User reviews + submits
  → TanStack Form validates against confirmSchema
  → useCreateAsset.mutate({ ...formValues, scan_job_id })
      → POST /assets via apiClient
  → onSuccess: navigate({ to: '/assets/new', search: { asset_id: response.asset_id } })
  → onError: display ApiError.message inline; no navigation
```

### Success Flow (Step 4)

```
User arrives at /assets/new?asset_id=X
  → Asset_Creation_Wizard detects Success_Step (asset_id present)
  → Displays "Asset X created and pending management approval."
  → "Create Another Asset" → navigate('/assets')
  → "View Asset List" → navigate('/assets')
```

### Approve Flow

```
User clicks ASSET_PENDING_APPROVAL row in asset list
  → navigate('/assets/{asset_id}/approve')
  → beforeLoad: checks context.userRole === 'management'
    → non-management: throw redirect({ to: '/unauthorized' })

User clicks "Approve"
  → Shows optional remarks textarea
  → Confirm: useApproveAsset.mutate({ action: 'APPROVE', remarks })
      → PUT /assets/{asset_id}/approve via apiClient
  → onSuccess: display new status + "Back to List" button
  → onError: display ApiError.message

User clicks "Reject"
  → Shows required rejection_reason textarea
  → Confirm button disabled while textarea is empty/whitespace
  → Confirm: useApproveAsset.mutate({ action: 'REJECT', rejection_reason })
  → onSuccess: display new status + "Back to List" button
  → onError: display ApiError.message
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Step Routing Completeness

*For any* combination of search params on `/assets/new`, the wizard renders exactly one step component (Confirm_Step or Success_Step) or redirects to `/assets` — never renders two steps simultaneously or a blank page.

**Validates: Requirements 1.1, 1.2, 1.3**

### Property 2: Upload Validation Gate

*For any* file selection where invoice count ≠ 1, or photo count < 1, or photo count > 5, or any file has an invalid MIME type, the `useUploadAsset` mutation must not be called and an inline validation error must be displayed.

**Validates: Requirements 3.6, 3.7, 3.8, 3.9**

### Property 3: Auth Header Exclusion on Presigned URLs

*For any* presigned URL PUT request issued during the upload flow, the request must not include an `Authorization` header.

**Validates: Requirements 4.3**

### Property 4: Upload Flow Sequencing

*For any* valid file selection (1 invoice + 1–5 photos), after `POST /assets/uploads` succeeds, exactly N PUT requests are made to the N presigned URLs returned in the response, where N equals the total file count.

**Validates: Requirements 4.1, 4.2**

### Property 5: Polling Interval Cleanup

*For any* `PollingStep` component lifecycle, the polling interval and animation interval are always cleared when the component unmounts, regardless of the current scan status at the time of unmount.

**Validates: Requirements 5.9**

### Property 6: Scan Completion Navigation

*For any* scan job that returns `status === "COMPLETED"`, the `PollingStep` navigates to `/assets/new?scan_job_id=X&ready=1` with `extracted_fields` present in the router navigation state.

**Validates: Requirements 5.7**

### Property 7: Confidence Threshold Styling

*For any* extracted field with `confidence < 0.8`, the corresponding form input must have the yellow border class (`border-warning`) applied. *For any* extracted field with `confidence >= 0.8`, the yellow border class must be absent.

**Validates: Requirements 6.5**

### Property 8: Extracted Field Rendering

*For any* `ExtractedFieldValue` object, the rendered field must display the confidence as a percentage label, and if `alternative_value` is non-empty, must display the alternative hint in the format "Alternative: {value}".

**Validates: Requirements 6.6, 6.7**

### Property 9: Confirm Form Submission Integrity

*For any* valid form submission on `Confirm_Step`, the `POST /assets` request body must include `scan_job_id` from the URL search param, and all required fields from the Zod schema must be present and valid.

**Validates: Requirements 7.1**

### Property 10: Asset List Pagination and Filter Params

*For any* page number or status filter change on the Asset List page, the `GET /assets` API call must include the updated `page` and `status` query params. Changing the status filter must reset `page` to 1.

**Validates: Requirements 9.1, 9.4, 9.6**

### Property 11: Pending Approval Row Navigation

*For any* asset row where `status === "ASSET_PENDING_APPROVAL"`, clicking the row must navigate to `/assets/{asset_id}/approve`.

**Validates: Requirements 9.10**

### Property 12: Management Role Guard

*For any* user with a role other than `"management"` (including `null`), accessing `/assets/:asset_id/approve` must redirect to `/unauthorized`.

**Validates: Requirements 10.2**

### Property 13: Rejection Reason Required

*For any* state where the rejection reason textarea is empty or whitespace-only, the reject confirm button must be disabled.

**Validates: Requirements 11.5**

### Property 14: Success Step Message Contains Asset ID

*For any* `asset_id` value read from the URL search param, the `Success_Step` rendered output must contain that exact `asset_id` string in the confirmation message.

**Validates: Requirements 8.1**

---

## Error Handling

| Scenario | Component | Handling |
|----------|-----------|----------|
| `POST /assets/uploads` fails | `UploadStep` | Display `ApiError.message` inline; do not proceed to S3 PUTs |
| Any S3 PUT fails | `UploadStep` | Display error inline; do not transition to `PollingStep` |
| Polling network/API error | `PollingStep` | Display error; `refetchInterval` returns `false` (stops polling) |
| `status === "SCAN_FAILED"` | `PollingStep` | Display `failure_reason`; modal stays open |
| `POST /assets` fails | `ConfirmAssetForm` | Display `ApiError.message` inline; do not navigate |
| `PUT /assets/{id}/approve` fails | `ApprovePage` | Display `ApiError.message`; do not show success state |
| `/assets/new` with no valid params | `Asset_Creation_Wizard` | `throw redirect({ to: '/assets' })` |
| Non-management accesses approve page | `beforeLoad` | `throw redirect({ to: '/unauthorized' })` |
| `extracted_fields` absent from router state | `ConfirmAssetForm` | Render form with empty defaults; no crash |

All `ApiError` instances expose `.message` from the backend JSON response body. Components read this from the mutation's `error` state (`(error as ApiError).message`).

---

## Testing Strategy

### Dual Testing Approach

Both unit tests and property-based tests are required and complementary:
- **Unit tests** cover specific examples, integration points, and edge cases
- **Property tests** verify universal invariants across randomized inputs

### Property-Based Testing

Use **fast-check** for TypeScript property-based testing. Each property test must run a minimum of **100 iterations** and include a comment tag referencing the design property:

```ts
// Feature: asset-creation-flow, Property 2: Upload Validation Gate
it.prop([fc.record({ invoiceCount: fc.integer({ min: 0, max: 3 }), photoCount: fc.integer({ min: 0, max: 7 }) })])(
  'rejects invalid file selections without calling the API',
  ({ invoiceCount, photoCount }) => { /* ... */ }
)
```

**Property test mapping:**

| Property | Arbitraries |
|----------|-------------|
| P1: Step routing completeness | `fc.record({ upload_session_id: fc.option(fc.string()), scan_job_id: fc.option(fc.string()), ready: fc.option(fc.integer()), asset_id: fc.option(fc.string()) })` |
| P2: Upload validation gate | `fc.record({ invoiceCount: fc.integer({min:0,max:3}), photoCount: fc.integer({min:0,max:7}) })` filtered to invalid cases |
| P3: Auth header exclusion | `fc.string()` for presigned URLs; assert `Authorization` absent from request headers |
| P4: Upload flow sequencing | `fc.array(fc.string(), {minLength:1, maxLength:5})` for photo files; assert PUT count equals file count |
| P5: Polling cleanup | `fc.constantFrom('PROCESSING', 'COMPLETED', 'SCAN_FAILED')` for status at unmount time |
| P6: Scan completion navigation | `fc.record({ status: fc.constant('COMPLETED'), extracted_fields: fc.dictionary(fc.string(), fc.record({...})) })` |
| P7: Confidence threshold styling | `fc.float({min:0, max:1})` for confidence; assert `border-warning` presence matches `< 0.8` |
| P8: Extracted field rendering | `fc.record({ confidence: fc.float({min:0,max:1}), alternative_value: fc.option(fc.string()) })` |
| P9: Confirm form submission integrity | `fc.record({...})` matching `confirmSchema` shape; assert `scan_job_id` in POST body |
| P10: Asset list pagination params | `fc.integer({min:1,max:100})` for page, `fc.constantFrom(...AssetStatuses, undefined)` for status |
| P11: Pending approval row navigation | `fc.string({minLength:1})` for asset_id; assert navigate called with correct path |
| P12: Management role guard | `fc.constantFrom('it-admin', 'employee', 'finance', null)` for non-management roles |
| P13: Rejection reason required | `fc.string()` filtered to whitespace-only; assert button `disabled` |
| P14: Success message contains asset_id | `fc.string({minLength:1})` for asset_id; assert rendered text contains it |

### Unit Tests

Focus on:
- `UploadStep` file validation logic — 0 invoices, >5 photos, wrong MIME type edge cases
- `ConfirmAssetForm` Zod schema — required field rejection, number coercion for `cost` and `approved_budget`
- `useScanJob` `refetchInterval` function — returns `false` for `COMPLETED` and `SCAN_FAILED`, `3000` for `PROCESSING`
- `useUploadAsset` — builds correct `FileManifestItem` array; plain `fetch` used for PUTs (not `apiClient`)
- `ApprovePage` — reject confirm button disabled when rejection reason is empty or whitespace
- `PollingStep` — shows `failure_reason` on `SCAN_FAILED`; does not navigate
- `Asset_Creation_Wizard` — redirects to `/assets` when params are incomplete

### Integration Tests

- Full upload → polling → confirm → success flow with mocked API responses
- Approve flow: management role succeeds; non-management role redirects to `/unauthorized`
- Asset list: pagination and status filter interaction updates query params correctly
