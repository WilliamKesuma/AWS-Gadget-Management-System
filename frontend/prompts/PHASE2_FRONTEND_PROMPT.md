# Frontend Implementation Prompt — Phase 2: Asset Assignment & Handover

## Context

You are building the React frontend for Phase 2 (Asset Assignment & Handover) of the Gadget Management System. The backend API is fully implemented. Users authenticate via Cognito and have one of these roles: `it-admin`, `management`, `employee`, `finance`. Every component and action described below must be conditionally rendered based on the user's role.

## User Roles

| Role | Value in token |
|------|---------------|
| IT Admin | `it-admin` |
| Management | `management` |
| Employee | `employee` |
| Finance | `finance` |

Assume the authenticated user's role is available from your auth context (e.g. `useAuth()` hook returning `{ user, role }`). Use this role to conditionally render components, buttons, and pages.

---

## API Endpoints

| Method | Path | Role(s) | Purpose |
|--------|------|---------|---------|
| POST | `/assets/{asset_id}/assign` | it-admin | Assign asset, generate handover PDF, send email — all in one call |
| GET | `/assets/{asset_id}/assign-pdf-form` | it-admin, employee | View/download handover form PDF |
| POST | `/assets/{asset_id}/signature-upload-url` | employee | Get presigned URL to upload signature |
| PUT | `/assets/{asset_id}/accept` | employee | Accept handover with signature |
| DELETE | `/assets/{asset_id}/cancel-assignment` | it-admin | Cancel pending assignment |
| GET | `/users/{employee_id}/signatures?page=&page_size=&sort_order=&assignment_date_from=&assignment_date_to=` | it-admin | List employee's handover signatures |

> There is no separate "Generate Handover Form" endpoint. The `POST /assign` endpoint handles assignment, PDF generation (via IronPDF), S3 upload, and SES email notification to the employee in a single request. The response includes a `presigned_url` for the generated PDF.

---

## TypeScript Types (already defined in `types.ts`)

```ts
// Assign Asset — single endpoint does assign + PDF + email
type AssignAssetRequest = { employee_id: string; notes?: string }
type AssignAssetResponse = {
    asset_id: string
    employee_id: string
    assignment_date: string
    status: AssetStatus       // will be "IN_STOCK" — status stays until employee accepts
    presigned_url: string     // presigned GET URL for the generated handover form PDF (60 min TTL)
}

// Cancel Assignment
type CancelAssignmentResponse = { asset_id: string; status: AssetStatus }

// View Handover Form
type GetHandoverFormResponse = { asset_id: string; presigned_url: string }

// Signature Upload
type GenerateSignatureUploadUrlResponse = { presigned_url: string; s3_key: string; asset_id: string }

// Accept Handover
type AcceptHandoverRequest = { signature_s3_key: string }
type AcceptHandoverResponse = { asset_id: string; status: AssetStatus; signed_form_url: string }

// List Employee Signatures (paginated)
type SignatureItem = {
    asset_id: string; brand?: string; model?: string;
    assignment_date: string; signature_timestamp: string; signature_url: string
}
```

All paginated list responses follow this shape:
```ts
{ items: T[]; count: number; total_items: number; total_pages: number; current_page: number }
```

---

## Features to Implement

### 1. Assign Asset to Employee (IT Admin only)

**Render condition:** `role === "it-admin"`

On the Asset Detail page, when the asset status is `IN_STOCK` and there is no pending handover, show an "Assign to Employee" button.

Clicking it opens a modal/dialog with:
- An employee selector (dropdown or searchable list). Fetch active employees from `GET /users?status=active&role=employee` to populate this.
- An optional "Notes" text field.
- A "Confirm Assignment" submit button.

On submit, call `POST /assets/{asset_id}/assign` with `{ employee_id, notes }`.

This single call does everything:
1. Creates the assignment record in DynamoDB
2. Generates a formal handover form PDF (with asset photos, IT Admin details, warranty info)
3. Uploads the PDF to S3
4. Sends an email notification to the employee via SES (mentioning only the device name)
5. Returns a `presigned_url` for the generated PDF

On success:
- Show a success toast/notification: "Asset assigned to {employee_name}. Handover form generated and email sent."
- Optionally offer to open the handover form PDF using the `presigned_url` from the response (open in new tab or show in an embedded viewer).
- Refresh the asset detail to reflect the updated state.

Handle these error cases with user-friendly messages:
- 409: "This Asset has been assigned to {name}" — show the name from the error response.
- 409: "This Asset is in progress to be assigned to {name}" — show the name.
- 409: "Asset must be in IN_STOCK status to be assigned" — the button should ideally be hidden when status ≠ IN_STOCK, but handle this as a fallback.
- 404: "Active employee not found" — the selected employee may have been deactivated.

---

### 2. View/Download Handover Form (IT Admin + Assigned Employee)

**Render condition:** `role === "it-admin"` OR (`role === "employee"` AND the employee is the assigned user for this asset)

On the Asset Detail page, when the asset has a pending or completed handover, show a "View Handover Form" button/link.

On click, call `GET /assets/{asset_id}/assign-pdf-form`.

Handle errors:
- 404: "Handover form has not been generated yet" — show a message. This should not normally happen since the assign endpoint now generates the form automatically.
- 404: "No assignment found for this asset" — no handover exists.
- 403: "You are not assigned to this asset" — hide the button or show an appropriate message.

On success, open the `presigned_url` in a new tab or display in an embedded PDF viewer (`<iframe>` or `<object>` tag).

---

### 3. Signature Upload & Accept Handover (Assigned Employee only)

**Render condition:** `role === "employee"` AND the employee is the assigned user AND asset status is `IN_STOCK` (meaning handover is pending acceptance)

This is a multi-step flow. On the Asset Detail page, show an "Accept Asset" button. Clicking it opens a modal/dialog with:

**Step 1 — Review & Download Form:**
- Show the asset details summary (brand, model, serial number, status).
- Show a "Download Handover Form" button that calls `GET /assets/{asset_id}/assign-pdf-form` and opens the PDF.
- After the form has been downloaded/viewed, unlock a checkbox: "I have read and reviewed the handover form."
- The checkbox must be checked before proceeding.

**Step 2 — Draw/Upload Signature:**
- Show a signature capture component (canvas-based drawing pad or file upload for a signature image).
- When the employee has their signature ready, call `POST /assets/{asset_id}/signature-upload-url` to get a presigned PUT URL.
- Upload the signature image (PNG) directly to S3 using the presigned PUT URL with `Content-Type: image/png`.
- Store the returned `s3_key` in component state.

**Step 3 — Accept Handover:**
- After the signature is uploaded, enable an "Agree & Accept Asset" confirmation button.
- On click, call `PUT /assets/{asset_id}/accept` with `{ signature_s3_key: s3_key }`.
- Handle errors:
  - 409: "Handover form must be generated before acceptance" — tell the employee to contact IT Admin.
  - 409: "Asset is not in a state that allows handover acceptance" — the asset may have already been accepted.
  - 400: "Signature image not found in S3" — the upload may have failed, prompt retry.

On success, show a confirmation message with the signed form URL (`signed_form_url`). Refresh the asset detail — status should now be `ASSIGNED`.

---

### 4. Cancel Pending Assignment (IT Admin only)

**Render condition:** `role === "it-admin"` AND asset status is `IN_STOCK` AND asset has a pending handover record (i.e. `assignment_date` exists on the asset)

On the Asset Detail page, show a "Cancel Assignment" button (styled as destructive/warning).

On click, show a confirmation dialog: "Are you sure you want to cancel this assignment? The asset will return to IN_STOCK."

On confirm, call `DELETE /assets/{asset_id}/cancel-assignment`.

Handle errors:
- 409: "Cannot cancel assignment after employee has accepted the handover" — the employee already signed.
- 404: "No pending assignment found for this asset" — assignment may have already been cancelled.

On success, refresh the asset detail. The asset should return to `IN_STOCK` with no assignment.

---

### 5. Employee Signatures List (IT Admin only)

**Render condition:** `role === "it-admin"`

On the User Detail page (for an employee user), show a "Handover Signatures" tab or section.

Call `GET /users/{employee_id}/signatures` with query params: `page`, `page_size`, `sort_order`, `assignment_date_from`, `assignment_date_to`.

Table columns:
| Column | Field |
|--------|-------|
| Asset ID | `asset_id` (link to asset detail) |
| Brand | `brand` |
| Model | `model` |
| Assignment Date | `assignment_date` (formatted) |
| Signed At | `signature_timestamp` (formatted) |
| Signature | `signature_url` (render as clickable thumbnail/link opening the image) |

Include:
- Pagination controls.
- Optional date range filter (`assignment_date_from`, `assignment_date_to`).

If no signatures exist, show: "No handover signatures on record."

---

## Conditional Rendering Summary

| Component / Action | it-admin | management | employee | finance |
|---|---|---|---|---|
| "Assign to Employee" button (IN_STOCK assets, no pending handover) | ✅ | ❌ | ❌ | ❌ |
| "View Handover Form" button | ✅ | ❌ | ✅ (assigned only) | ❌ |
| "Accept Asset" button + signature flow | ❌ | ❌ | ✅ (assigned only, IN_STOCK) | ❌ |
| "Cancel Assignment" button | ✅ | ❌ | ❌ | ❌ |
| "Employee Signatures" section on user detail | ✅ | ❌ | ❌ | ❌ |

---

## Asset Detail Page — Conditional Action Buttons

On the Asset Detail page, render action buttons based on both role AND asset status:

```
if role === "it-admin":
    if status === "IN_STOCK" AND no pending handover (no assignment_date):
        → Show "Assign to Employee"
    if status === "IN_STOCK" AND has pending handover (assignment_date exists):
        → Show "View Handover Form"
        → Show "Cancel Assignment"
    if status === "ASSIGNED":
        → Show "View Handover Form"

if role === "employee":
    if status === "IN_STOCK" AND employee is the assigned user (assignment_date exists):
        → Show "View Handover Form"
        → Show "Accept Asset" (opens modal with download form → checkbox → signature → accept)
    if status === "ASSIGNED" AND employee is the assigned user:
        → Show "View Handover Form" (signed version)
```

---

## How to Detect Pending Handover

The `GET /assets` list endpoint returns an `assignment_date` field for each asset. If `assignment_date` is present and non-null, the asset has a pending or completed handover:
- `status === "IN_STOCK"` + `assignment_date` exists → pending handover (employee hasn't accepted yet)
- `status === "ASSIGNED"` + `assignment_date` exists → completed handover (employee accepted)
- `status === "IN_STOCK"` + no `assignment_date` → no handover, available for assignment

The `GET /assets/{asset_id}` detail endpoint does not currently return `assignment_date`. To determine if a pending handover exists on the detail page, you can either:
1. Call `GET /assets/{asset_id}/assign-pdf-form` and check if it returns 404 ("No assignment found") — if it succeeds, a handover exists.
2. Use the `assignment_date` from the list view and pass it via route state/context.

---

## Error Response Format

The API returns errors in the shape: `{ "message": "..." }`. Always display the `message` field to the user for 4xx errors, as they contain contextual information (e.g. employee names in 409 conflict messages).

---

## Notes

- There is no separate "Generate Handover Form" button or endpoint. The `POST /assign` endpoint handles everything — assignment, PDF generation, S3 upload, and SES email — in a single call. The old `POST /assets/{asset_id}/handover-form` endpoint has been removed.
- The employee receives an email notification (via SES) when an asset is assigned to them. The email mentions only the device name (Brand + Model). This happens server-side — no frontend action needed.
- Presigned URLs expire after 60 minutes (handover form) or 15 minutes (signature upload). Handle expiry gracefully — if a fetch fails with 403 from S3, prompt the user to refresh.
- The signature upload to S3 is a direct PUT to the presigned URL, not through your API. Use `fetch(presignedUrl, { method: 'PUT', body: imageBlob, headers: { 'Content-Type': 'image/png' } })`.
- The handover form is a PDF. Consider using an inline `<iframe>` or `<object>` tag for preview.