# Frontend Implementation Prompt — Phase 5: Asset Return Process

## Context

You are building the React frontend for Phase 5 (Asset Return Process) of the Gadget Management System. The backend API is fully implemented. Every component and action described below must be conditionally rendered based on the user's role.

The return flow is split between two actors:

*   **IT Admin** initiates the return, uploads evidence (photos + admin signature), and submits to notify the employee.
*   **Employee** receives a notification, reviews the return details, uploads their digital signature, and completes the return.

---

## API Endpoints

| Method | Path | Role(s) | Purpose |
| --- | --- | --- | --- |
| POST | `/assets/{asset_id}/returns` | it-admin | Initiate a return for an assigned asset |
| GET | `/assets/{asset_id}/returns` | it-admin | List all returns for an asset (paginated, filterable) |
| GET | `/assets/{asset_id}/returns/{return_id}` | it-admin, employee | View details of a specific return |
| POST | `/assets/{asset_id}/returns/{return_id}/upload-urls` | it-admin | Generate presigned PUT URLs for return photos and admin signature |
| POST | `/assets/{asset_id}/returns/{return_id}/submit-evidence` | it-admin | Validate evidence exists in S3 and notify employee via email |
| POST | `/assets/{asset_id}/returns/{return_id}/signature-upload-url` | employee | Generate presigned PUT URL for employee's digital signature |
| PUT | `/assets/{asset_id}/returns/{return_id}/complete` | employee | Complete the return by submitting the employee signature key |
| GET | `/assets/pending-returns` | it-admin | List assets with approved replacement issues awaiting return |
| GET | `/users/me/pending-signatures` | employee | List pending return (and handover) signature tasks for the employee |

---

## TypeScript Types (already defined in `types.ts`)

```typescript
// Enums
type ReturnTrigger = "RESIGNATION" | "REPLACEMENT" | "TRANSFER" | "IT_RECALL" | "UPGRADE"
type ReturnCondition = "GOOD" | "MINOR_DAMAGE" | "MINOR_DAMAGE_REPAIR_REQUIRED" | "MAJOR_DAMAGE"
type ResetStatus = "COMPLETE" | "INCOMPLETE"
type AssetStatus =
    | "IN_STOCK" | "ASSIGNED" | "ASSET_PENDING_APPROVAL" | "ASSET_REJECTED"
    | "DISPOSAL_REVIEW" | "DISPOSAL_PENDING"
    | "DISPOSED" | "RETURN_PENDING" | "DAMAGED"
    | "UNDER_REPAIR" | "ISSUE_REPORTED"

// Initiate Return (IT Admin)
type InitiateReturnRequest = {
    return_trigger: ReturnTrigger
    remarks: string
    condition_assessment: ReturnCondition
    reset_status: ResetStatus
}

type InitiateReturnResponse = {
    asset_id: string
    return_id: string
    status: AssetStatus  // "RETURN_PENDING"
}

// Generate Return Upload URLs (IT Admin — photos + admin signature only)
type ReturnFileManifestItemType = "photo" | "admin-signature"

type ReturnFileManifestItem = {
    name: string
    type: ReturnFileManifestItemType
}

type GenerateReturnUploadUrlsRequest = {
    files: ReturnFileManifestItem[]
}

type ReturnPresignedUrlItem = {
    file_key: string
    presigned_url: string
    type: string
}

type GenerateReturnUploadUrlsResponse = {
    upload_urls: ReturnPresignedUrlItem[]
}

// Submit Admin Evidence (IT Admin)
type SubmitAdminReturnEvidenceResponse = {
    asset_id: string
    return_id: string
    message: string
}

// Generate Employee Signature Upload URL (Employee)
type GenerateReturnSignatureUploadUrlRequest = {
    file_name: string
}

type GenerateReturnSignatureUploadUrlResponse = {
    presigned_url: string
    s3_key: string
    return_id: string
    asset_id: string
}

// Complete Return (Employee)
type CompleteReturnRequest = {
    user_signature_s3_key: string
}

type CompleteReturnResponse = {
    asset_id: string
    new_status: AssetStatus
    completed_at: string
}

// Get Return Detail (IT Admin + Employee)
type GetReturnResponse = {
    asset_id: string
    return_id: string
    return_trigger: ReturnTrigger
    initiated_by: string
    initiated_by_id: string
    initiated_at: string
    condition_assessment: ReturnCondition
    remarks: string
    reset_status: ResetStatus
    serial_number?: string
    model?: string
    return_photo_urls?: string[]
    admin_signature_url?: string
    user_signature_url?: string
    completed_at?: string
    completed_by?: string
    completed_by_id?: string
    resolved_status?: AssetStatus
    asset_status: AssetStatus
}

// List Returns (IT Admin)
type ListReturnsFilter = PaginatedAPIFilter & {
    return_trigger?: ReturnTrigger
    condition_assessment?: ReturnCondition
}

type ReturnListItem = {
    asset_id: string
    return_id: string
    return_trigger: ReturnTrigger
    initiated_by: string
    initiated_by_id: string
    initiated_at: string
    condition_assessment: ReturnCondition
    remarks: string
    reset_status: ResetStatus
    resolved_status?: AssetStatus
    completed_at?: string
}

type ListReturnsResponse = PaginatedAPIResponse<ReturnListItem>

// Pending Returns (IT Admin — assets with approved replacement issues)
type PendingReturnItem = {
    asset_id: string
    brand?: string
    model?: string
    serial_number?: string
    assignee_user_id?: string
    assignee_fullname?: string
    replacement_approved_at: string
    replacement_justification?: string
    management_remarks?: string
    issue_id: string
}

type ListPendingReturnsResponse = PaginatedAPIResponse<PendingReturnItem>

// Pending Signatures (Employee — pending return + handover signatures)
type DocumentType = "handover" | "return"

type PendingSignatureItem = {
    document_type: DocumentType
    asset_id: string
    record_id: string
    // handover-specific
    employee_name?: string
    assignment_date?: string
    handover_form_s3_key?: string
    // return-specific
    return_trigger?: ReturnTrigger
    initiated_at?: string
}

type ListPendingSignaturesResponse = PaginatedAPIResponse<PendingSignatureItem>
```

---

## Return Flow Overview

```
IT Admin selects an ASSIGNED asset
    │
    ▼  (Feature 1) POST /assets/{asset_id}/returns
    Fills in: return_trigger, remarks, condition_assessment, reset_status
    → Asset status: RETURN_PENDING
    → Return record created (serial_number + model auto-fetched from DDB)
    │
    ▼  (Feature 2) POST /assets/{asset_id}/returns/{return_id}/upload-urls
    Generates presigned PUT URLs for:
      - 1+ photos (type: "photo")
      - 1 admin signature drawn via react-signature-canvas (type: "admin-signature")
    Uploads files directly to S3 via presigned PUT URLs
    │
    ▼  (Feature 3) POST /assets/{asset_id}/returns/{return_id}/submit-evidence
    Backend validates S3 evidence exists, sends SES email to employee
    │
    ▼  Employee receives email notification
    │
    ▼  (Feature 5) GET /users/me/pending-signatures  [Employee]
    Employee sees pending return signature task in their dashboard
    │
    ▼  (Feature 4) GET /assets/{asset_id}/returns/{return_id}  [Employee]
    Employee views return details (condition, photos, admin signature)
    │
    ▼  (Feature 6) POST /assets/{asset_id}/returns/{return_id}/signature-upload-url  [Employee]
    Employee draws signature via react-signature-canvas
    Gets presigned PUT URL, uploads signature PNG to S3
    │
    ▼  (Feature 7) PUT /assets/{asset_id}/returns/{return_id}/complete  [Employee]
    Employee submits user_signature_s3_key
    Backend validates all evidence, transitions asset to final status:
      GOOD                       → IN_STOCK
      MINOR_DAMAGE               → DAMAGED
      MINOR_DAMAGE_REPAIR_REQUIRED → ISSUE_REPORTED (auto-creates issue)
      MAJOR_DAMAGE               → DISPOSAL_REVIEW
```

---

## Features to Implement

### 1\. Initiate Return (IT Admin only)

**Render condition:** `role === "it-admin"` AND asset status is `ASSIGNED`

On the Asset Detail page, show an "Initiate Return" button.

Clicking it opens a modal/dialog with a form containing:

*   **Return Trigger** — dropdown (required): `RESIGNATION`, `REPLACEMENT`, `TRANSFER`, `IT_RECALL`, `UPGRADE`
*   **Condition Assessment** — dropdown (required): `GOOD`, `MINOR_DAMAGE`, `MINOR_DAMAGE_REPAIR_REQUIRED`, `MAJOR_DAMAGE`
*   **Reset Status** — radio buttons (required): `COMPLETE`, `INCOMPLETE`
*   **Remarks** — textarea (required, describe the reason for return)

> Note: `serial_number` and `model` are NOT form fields — they are auto-fetched from the asset record by the backend.

On submit, call `POST /assets/{asset_id}/returns` with the `InitiateReturnRequest` body.

On success:

*   Show a success toast: "Return initiated. Asset is now pending return."
*   Close the modal and refresh the asset detail view. Asset status becomes `RETURN_PENDING`.
*   Proceed immediately to Feature 2 (upload evidence) using the `return_id` from the response.

Handle these error cases:

*   400 (ValidationError): Display the validation message.
*   409 "Device factory reset must be completed before the return can be initiated" — `reset_status` is `INCOMPLETE`. Show this message inline on the form before submission, or as an error toast.
*   409 "Asset is not in ASSIGNED status" — the asset has already been returned or is in another state.
*   404: "Asset not found"

---

### 2\. Upload Return Evidence (IT Admin only)

**Render condition:** `role === "it-admin"` AND asset status is `RETURN_PENDING` AND the current user initiated the return

This step follows immediately after Feature 1 (or can be accessed from the Return Detail page). It is a two-part upload: photos and admin signature.

#### Part A — Upload Return Photos

Allow the IT Admin to select one or more photo files (JPEG/PNG).

Prepare a file manifest:

```typescript
const request: GenerateReturnUploadUrlsRequest = {
    files: [
        { name: "front-view.jpg", type: "photo" },
        { name: "back-view.jpg", type: "photo" }
    ]
}
```

Call `POST /assets/{asset_id}/returns/{return_id}/upload-urls`.

For each URL in the response where `type === "photo"`, upload the file directly to S3:

```typescript
await fetch(presignedUrl, {
    method: 'PUT',
    body: fileBlob,
    headers: { 'Content-Type': 'image/jpeg' }
})
```

#### Part B — Admin Signature

Use `react-signature-canvas` to capture the IT Admin's digital signature.

```
import SignatureCanvas from 'react-signature-canvas'

<SignatureCanvas
    ref={sigCanvasRef}
    penColor="black"
    canvasProps={{ width: 500, height: 200, className: 'signature-canvas' }}
/>
<button onClick={() => sigCanvasRef.current?.clear()}>Clear</button>
```

When the admin is done signing:

1.  Export the signature as a PNG blob: `sigCanvasRef.current?.getTrimmedCanvas().toBlob(...)`
2.  Include it in the upload manifest as `{ name: "admin-signature.png", type: "admin-signature" }`.
3.  Call `POST /assets/{asset_id}/returns/{return_id}/upload-urls` (can be combined with photos in a single request).
4.  Upload the PNG blob to the presigned URL where `type === "admin-signature"`.

After all uploads complete, proceed to Feature 3 (submit evidence).

Handle errors:

*   400: "At least one photo file is required" — no photos selected.
*   403: "Insufficient permissions"
*   404: "Asset not found" or "Return record not found"
*   409: "Asset is not in RETURN\_PENDING status"

---

### 3\. Submit Admin Evidence (IT Admin only)

**Render condition:** `role === "it-admin"` AND asset status is `RETURN_PENDING`

After all files are uploaded to S3, call `POST /assets/{asset_id}/returns/{return_id}/submit-evidence` (no request body).

On success:

*   Show a success toast: "Evidence submitted. Employee has been notified to provide their signature."
*   Refresh the return detail view.

The backend validates that all S3 files exist and sends an SES email to the assigned employee. This is a server-side action — no frontend handling needed for the email.

Handle errors:

*   400 "Return photo evidence has not been uploaded" — photos were not successfully uploaded to S3.
*   400 "Admin signature has not been uploaded" — admin signature was not successfully uploaded to S3.
*   404: "Asset not found" or "Return record not found"
*   409: "Asset is not in RETURN\_PENDING status"

---

### 4\. View Return Detail (IT Admin + Employee)

**Render condition:** `role === "it-admin"` OR (`role === "employee"` AND the employee is the assigned user for this asset)

Call `GET /assets/{asset_id}/returns/{return_id}`.

**Display fields:**

| Section | Fields |
| --- | --- |
| Return Info | `return_trigger` (formatted label), `initiated_by`, `initiated_at` (formatted date) |
| Device Info | `serial_number`, `model` (show "N/A" if not present) |
| Condition | `condition_assessment` (formatted label + badge), `reset_status` (badge), `remarks` |
| Admin Evidence | `return_photo_urls` — gallery of clickable thumbnails. `admin_signature_url` — render as an `<img>` tag. Show "Not yet uploaded" if null. |
| Employee Evidence | `user_signature_url` — render as an `<img>` tag. Show "Pending employee signature" if null. |
| Completion | `completed_by`, `completed_at`, `resolved_status` (badge) — show only when `completed_at` is present |
| Asset Status | `asset_status` (badge) |

**Conditional action buttons on the detail view:**

*   If `role === "it-admin"` AND `asset_status === "RETURN_PENDING"` AND `admin_signature_url` is null → Show "Upload Evidence" button (navigates to Feature 2)
*   If `role === "it-admin"` AND `asset_status === "RETURN_PENDING"` AND `admin_signature_url` is present AND `user_signature_url` is null → Show "Re-notify Employee" button (calls Feature 3 again)
*   If `role === "employee"` AND `asset_status === "RETURN_PENDING"` AND `user_signature_url` is null → Show "Sign & Complete Return" button (opens Feature 6/7 flow)

Handle errors:

*   403: "You do not have access to this return record" — employee is not the assigned user.
*   404: "Asset not found" or "Return record not found"

---

### 5\. Pending Signatures Dashboard (Employee only)

**Render condition:** `role === "employee"`

This is the employee's action inbox. Create a dedicated page or section accessible from the main navigation: "Pending Signatures".

Call `GET /users/me/pending-signatures` with query params: `page`, `page_size`.

The response contains both handover and return signature tasks. Filter by `document_type === "return"` to show only return tasks on this page (or show all in a unified list with a type badge).

**Table columns:**

| Column | Field | Notes |
| --- | --- | --- |
| Type | `document_type` | Badge: "Return" or "Handover" |
| Asset ID | `asset_id` | Link to return/handover detail |
| Return Trigger | `return_trigger` | Formatted label (return tasks only) |
| Initiated At | `initiated_at` | Formatted date (return tasks only) |
| Actions | — | "View & Sign" button |

Clicking "View & Sign" navigates to the Return Detail page (Feature 4) for that `asset_id` + `record_id`.

If no pending signatures exist, show: "No pending signatures."

---

### 6\. Employee Signature Upload (Employee only)

**Render condition:** `role === "employee"` AND asset status is `RETURN_PENDING` AND employee is the assigned user

This is triggered from the Return Detail page (Feature 4) via the "Sign & Complete Return" button.

Open a modal/dialog containing:

*   A read-only summary of the return details (trigger, condition, remarks, device info)
*   A `react-signature-canvas` component for the employee to draw their signature

```
import SignatureCanvas from 'react-signature-canvas'

<SignatureCanvas
    ref={sigCanvasRef}
    penColor="black"
    canvasProps={{ width: 500, height: 200, className: 'signature-canvas' }}
/>
<button onClick={() => sigCanvasRef.current?.clear()}>Clear</button>
```

On "Submit Signature":

1.  Export the signature as a PNG blob.
2.  Call `POST /assets/{asset_id}/returns/{return_id}/signature-upload-url` with body `{ file_name: "user-signature.png" }`.
3.  Upload the PNG blob to the returned `presigned_url` via `PUT`.
4.  Store the returned `s3_key` for use in Feature 7.

Handle errors:

*   403: "You are not assigned to this asset"
*   404: "Asset not found" or "Return record not found"
*   409: "Asset is not in RETURN\_PENDING status"

---

### 7\. Complete Return (Employee only)

**Render condition:** `role === "employee"` AND asset status is `RETURN_PENDING` AND employee is the assigned user

This step follows immediately after Feature 6 (signature upload). After the signature is successfully uploaded to S3, call `PUT /assets/{asset_id}/returns/{return_id}/complete` with:

```typescript
const request: CompleteReturnRequest = {
    user_signature_s3_key: s3_key  // from Feature 6 response
}
```

On success:

*   Show a success toast: "Return completed successfully."
*   Close the modal and navigate the employee away from the asset (e.g., to their "My Assets" page), since the asset is no longer assigned to them.
*   The asset transitions to its final status based on condition:

| Condition | Final Asset Status |
| --- | --- |
| `GOOD` | `IN_STOCK` |
| `MINOR_DAMAGE` | `DAMAGED` |
| `MINOR_DAMAGE_REPAIR_REQUIRED` | `ISSUE_REPORTED` |
| `MAJOR_DAMAGE` | `DISPOSAL_REVIEW` |

Handle errors:

*   400 "Return photo evidence has not been uploaded" — admin photos missing from S3.
*   400 "Admin signature has not been uploaded" — admin signature missing from S3.
*   400 "User signature has not been uploaded" — the signature upload in Feature 6 failed silently.
*   403: "You are not assigned to this asset"
*   404: "Asset not found" or "Return record not found"
*   409: "Asset is not in RETURN\_PENDING status"

---

### 8\. List Returns for Asset (IT Admin only)

**Render condition:** `role === "it-admin"`

On the Asset Detail page, show a "Returns" tab or section.

Call `GET /assets/{asset_id}/returns` with optional query params: `page`, `page_size`, `return_trigger`, `condition_assessment`, `sort_order`.

**Table columns:**

| Column | Field | Notes |
| --- | --- | --- |
| Return Trigger | `return_trigger` | Formatted label |
| Condition | `condition_assessment` | Colored badge |
| Reset Status | `reset_status` | Badge |
| Initiated By | `initiated_by` | Resolved user name |
| Initiated At | `initiated_at` | Formatted date |
| Status | `resolved_status` | Badge — show "Pending" if null |
| Completed At | `completed_at` | Formatted date, show "—" if null |
| Actions | — | Link to return detail |

Include pagination controls and optional filters for `return_trigger` and `condition_assessment`.

If no returns exist, show: "No returns recorded for this asset."

---

### 9\. Pending Returns List (IT Admin only)

**Render condition:** `role === "it-admin"`

Create a dedicated page or section accessible from the main navigation: "Pending Returns".

This lists assets that have an approved replacement issue and are awaiting a return to be initiated (i.e., the IT Admin needs to call Feature 1 for these assets).

Call `GET /assets/pending-returns` with query params: `page`, `page_size`.

**Table columns:**

| Column | Field | Notes |
| --- | --- | --- |
| Asset ID | `asset_id` | Link to asset detail |
| Brand / Model | `brand`, `model` | Combined display |
| Serial Number | `serial_number` | Show "N/A" if null |
| Assigned To | `assignee_fullname` | Employee name |
| Replacement Approved At | `replacement_approved_at` | Formatted date |
| Replacement Justification | `replacement_justification` | Truncate if long |
| Management Remarks | `management_remarks` | Truncate if long |
| Actions | — | "Initiate Return" button |

Clicking "Initiate Return" navigates to the Asset Detail page for that asset and opens the Initiate Return modal (Feature 1).

If no pending returns exist, show: "No assets pending return."

---

## Conditional Rendering Summary

| Component / Action | it-admin | management | employee | finance |
| --- | --- | --- | --- | --- |
| "Initiate Return" button (ASSIGNED asset) | ✅ | ❌ | ❌ | ❌ |
| "Upload Evidence" (after initiation) | ✅ | ❌ | ❌ | ❌ |
| "Submit Evidence" (after S3 upload) | ✅ | ❌ | ❌ | ❌ |
| Return Detail view | ✅ | ❌ | ✅ (assigned only) | ❌ |
| "Sign & Complete Return" button (RETURN\_PENDING) | ❌ | ❌ | ✅ (assigned only) | ❌ |
| Returns tab on Asset Detail | ✅ | ❌ | ❌ | ❌ |
| "Pending Returns" page/nav item | ✅ | ❌ | ❌ | ❌ |
| "Pending Signatures" page/nav item | ❌ | ❌ | ✅ | ❌ |

---

## Status Badge Colors

Use consistent color coding for asset statuses relevant to the return flow:

| Status | Color | Label |
| --- | --- | --- |
| `ASSIGNED` | success | Assigned |
| `RETURN_PENDING` | warning | Return Pending |
| `IN_STOCK` | success | In Stock |
| `DAMAGED` | danger | Damaged |
| `ISSUE_REPORTED` | warning | Issue Reported |
| `DISPOSAL_REVIEW` | danger | Disposal Review |

For condition assessment badges:

| Condition | Color | Label |
| --- | --- | --- |
| `GOOD` | success | Good |
| `MINOR_DAMAGE` | warning | Minor Damage |
| `MINOR_DAMAGE_REPAIR_REQUIRED` | warning | Minor Damage — Repair Required |
| `MAJOR_DAMAGE` | danger | Major Damage |

For reset status badges:

| Reset Status | Color | Label |
| --- | --- | --- |
| `COMPLETE` | success | Reset Complete |
| `INCOMPLETE` | danger | Reset Incomplete |

---

## Notes

*   The `reset_status` field is validated server-side: if `INCOMPLETE` is submitted, the backend returns 409. You may also add a client-side warning in the form before submission: "Device must be factory reset before initiating a return."
*   `serial_number` and `model` are auto-fetched from the asset record by the backend at initiation time — do NOT include them as form fields.
*   The employee signature and admin signature are both captured using `react-signature-canvas`. Export as PNG blob and upload via presigned PUT URL. The `Content-Type` header for the PUT request should be `image/png`.
*   Presigned PUT URLs expire after 15 minutes. If an upload fails with a 403 from S3, prompt the user to restart the upload step.
*   Presigned GET URLs for viewing photos and signatures are generated fresh on each `GetReturn` call and expire after 15 minutes. If a photo or signature fails to load, prompt the user to refresh the page.
*   The `GenerateReturnUploadUrls` endpoint accepts both photos and admin signature in a single request. You can batch them together or call the endpoint twice — once for photos, once for the signature.
*   The `submit-evidence` endpoint (Feature 3) has no request body. It is a POST with an empty body that triggers server-side S3 validation and SES email delivery.
*   The `ListPendingSignatures` endpoint returns both `"handover"` and `"return"` document types. Use `document_type` to distinguish them and render the appropriate detail view.
*   After `CompleteReturn` succeeds, the asset is no longer assigned to the employee. Navigate them away from the asset detail page to avoid a stale view.
*   The IT Admin can re-call `submit-evidence` (Feature 3) to re-send the notification email to the employee if needed. This is safe to call multiple times.