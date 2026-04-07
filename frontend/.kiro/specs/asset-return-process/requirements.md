# Requirements Document

## Introduction

This feature implements the Asset Return Process (Phase 5) for the Gadget Management System frontend. The return flow is split between two actors: the IT Admin initiates the return, uploads photographic evidence and a digital signature, then submits to notify the employee. The employee then reviews the return details, draws their own digital signature, and completes the return. The feature covers nine distinct capabilities: initiating a return, uploading admin evidence, submitting evidence, viewing return details, a pending-signatures dashboard for employees, employee signature upload, completing the return, listing returns per asset, and a pending-returns list for IT Admins.

## Glossary

- **Return_Process**: The end-to-end workflow for reclaiming an assigned asset from an employee.
- **IT_Admin**: A user with role `it-admin` who initiates and manages the return process.
- **Employee**: A user with role `employee` who is the current assignee of the asset being returned.
- **Return_Record**: The backend record created when a return is initiated, identified by `return_id`.
- **Return_Trigger**: The reason for the return — one of `RESIGNATION`, `REPLACEMENT`, `TRANSFER`, `IT_RECALL`, `UPGRADE`.
- **Condition_Assessment**: The physical condition of the asset at return time — one of `GOOD`, `MINOR_DAMAGE`, `MINOR_DAMAGE_REPAIR_REQUIRED`, `MAJOR_DAMAGE`.
- **Reset_Status**: Whether the device has been factory-reset — `COMPLETE` or `INCOMPLETE`.
- **Admin_Evidence**: One or more return photos plus the IT Admin's digital signature, uploaded to S3 via presigned PUT URLs.
- **Employee_Signature**: The employee's digital signature, uploaded to S3 via a presigned PUT URL.
- **Presigned_URL**: A time-limited AWS S3 URL used to upload or retrieve a file directly without backend involvement.
- **Signature_Canvas**: The `react-signature-canvas` component used to capture digital signatures as PNG blobs.
- **Pending_Return**: An asset that has an approved replacement issue and is awaiting a return to be initiated by the IT Admin.
- **Pending_Signature**: An employee's outstanding task to sign and complete a return (or handover).
- **DataTable**: The `@tanstack/react-table`-based `DataTable` component used for all tabular data.
- **TanStack_Form**: The `@tanstack/react-form` + Zod form library used for all form state and validation.
- **TanStack_Query**: The `@tanstack/react-query` library used for all server state management.
- **TanStack_Router**: The `@tanstack/react-router` file-based router used for all navigation and URL state.

---

## Requirements

### Requirement 1: Initiate Return (IT Admin)

**User Story:** As an IT Admin, I want to initiate a return for an assigned asset, so that I can formally begin the asset recovery process and transition the asset to `RETURN_PENDING` status.

#### Acceptance Criteria

1. WHEN the asset status is `ASSIGNED` AND the current user role is `it-admin`, THE Asset_Detail_Page SHALL render an "Initiate Return" button in the Quick Actions section.
2. WHEN the IT_Admin clicks "Initiate Return", THE Initiate_Return_Dialog SHALL open and display a form with fields: Return Trigger (required dropdown), Condition Assessment (required dropdown), Reset Status (required radio group: `COMPLETE` / `INCOMPLETE`), and Remarks (required textarea).
3. THE Initiate_Return_Dialog SHALL NOT include `serial_number` or `model` as form fields, as these are auto-fetched by the backend.
4. WHEN the IT_Admin submits the form with all valid fields, THE Return_Process SHALL call `POST /assets/{asset_id}/returns` with the `InitiateReturnRequest` body.
5. WHEN the `POST /assets/{asset_id}/returns` call succeeds, THE Asset_Detail_Page SHALL show a success toast "Return initiated. Asset is now pending return.", close the dialog, and invalidate the asset detail query so the status refreshes to `RETURN_PENDING`.
6. WHEN the `POST /assets/{asset_id}/returns` call succeeds, THE Return_Process SHALL immediately open the Upload Evidence dialog (Requirement 2) using the `return_id` from the response.
7. IF the API returns a 400 validation error, THEN THE Initiate_Return_Dialog SHALL display the error message inline below the form.
8. IF the API returns a 409 error with message "Device factory reset must be completed before the return can be initiated", THEN THE Initiate_Return_Dialog SHALL display this message as an inline form error.
9. IF the API returns a 409 error with message "Asset is not in ASSIGNED status", THEN THE Return_Process SHALL show a `toast.error()` with the API message.
10. IF the API returns a 404 error, THEN THE Return_Process SHALL show a `toast.error()` with the API message.
11. WHERE the user role is NOT `it-admin` OR the asset status is NOT `ASSIGNED`, THE Asset_Detail_Page SHALL NOT render the "Initiate Return" button.
12. THE Initiate_Return_Form SHALL use TanStack_Form with a Zod schema validating that `return_trigger`, `condition_assessment`, `reset_status`, and `remarks` are all present and non-empty.

---

### Requirement 2: Upload Return Evidence (IT Admin)

**User Story:** As an IT Admin, I want to upload return photos and my digital signature after initiating a return, so that I can provide evidence of the asset's condition before notifying the employee.

#### Acceptance Criteria

1. WHEN the asset status is `RETURN_PENDING` AND the current user role is `it-admin`, THE Upload_Evidence_Dialog SHALL be accessible either immediately after Requirement 1 succeeds or via an "Upload Evidence" button on the Return Detail page when `admin_signature_url` is null.
2. THE Upload_Evidence_Dialog SHALL present a two-part upload flow: Part A for return photos and Part B for the admin signature.
3. WHEN the IT_Admin selects one or more JPEG or PNG files in Part A, THE Upload_Evidence_Dialog SHALL display the selected file names and allow removal before upload.
4. WHEN the IT_Admin is ready to upload, THE Return_Process SHALL call `POST /assets/{asset_id}/returns/{return_id}/upload-urls` with a `GenerateReturnUploadUrlsRequest` containing all selected photo files (type `"photo"`) and the admin signature file (type `"admin-signature"`) in a single request.
5. WHEN the presigned URLs are returned, THE Return_Process SHALL upload each file directly to S3 via `PUT` with the appropriate `Content-Type` header (`image/jpeg` or `image/png` for photos, `image/png` for the signature).
6. THE Upload_Evidence_Dialog SHALL render a `Signature_Canvas` component (via `react-signature-canvas`) in Part B, with a "Clear" button to reset the canvas.
7. WHEN the IT_Admin submits the upload form, THE Return_Process SHALL export the signature canvas as a PNG blob and include it in the upload manifest as `{ name: "admin-signature.png", type: "admin-signature" }`.
8. IF any S3 PUT request returns a 403 status, THEN THE Upload_Evidence_Dialog SHALL show a `toast.error()` prompting the user to restart the upload step, as the presigned URL has expired.
9. IF the API returns a 400 error "At least one photo file is required", THEN THE Upload_Evidence_Dialog SHALL display this as an inline form error.
10. IF the API returns a 403 or 404 error, THEN THE Return_Process SHALL show a `toast.error()` with the API message.
11. IF the API returns a 409 error "Asset is not in RETURN_PENDING status", THEN THE Return_Process SHALL show a `toast.error()` with the API message.
12. WHEN all uploads complete successfully, THE Return_Process SHALL automatically proceed to Requirement 3 (Submit Evidence).
13. WHERE the user role is NOT `it-admin`, THE Upload_Evidence_Dialog SHALL NOT be accessible.

---

### Requirement 3: Submit Admin Evidence (IT Admin)

**User Story:** As an IT Admin, I want to submit the uploaded evidence to the backend, so that the system validates the S3 files and sends an email notification to the employee.

#### Acceptance Criteria

1. WHEN all files have been successfully uploaded to S3, THE Return_Process SHALL call `POST /assets/{asset_id}/returns/{return_id}/submit-evidence` with an empty body.
2. WHEN the `submit-evidence` call succeeds, THE Return_Process SHALL show a success toast "Evidence submitted. Employee has been notified to provide their signature." and refresh the Return Detail view.
3. WHEN the asset status is `RETURN_PENDING` AND `admin_signature_url` is present AND `user_signature_url` is null, THE Return_Detail_Page SHALL render a "Re-notify Employee" button for the IT_Admin that calls `POST /assets/{asset_id}/returns/{return_id}/submit-evidence` again.
4. IF the API returns a 400 error "Return photo evidence has not been uploaded", THEN THE Return_Process SHALL show a `toast.error()` with the API message.
5. IF the API returns a 400 error "Admin signature has not been uploaded", THEN THE Return_Process SHALL show a `toast.error()` with the API message.
6. IF the API returns a 404 or 409 error, THEN THE Return_Process SHALL show a `toast.error()` with the API message.
7. WHERE the user role is NOT `it-admin`, THE Return_Detail_Page SHALL NOT render the "Re-notify Employee" button.

---

### Requirement 4: View Return Detail (IT Admin and Employee)

**User Story:** As an IT Admin or assigned Employee, I want to view the full details of a return record, so that I can review the return status, evidence, and take appropriate actions.

#### Acceptance Criteria

1. THE Return_Detail_Page SHALL be accessible at a route under the asset detail (e.g. `/assets/{asset_id}/returns/{return_id}`) and SHALL call `GET /assets/{asset_id}/returns/{return_id}` to load the data.
2. THE Return_Detail_Page SHALL display the following sections: Return Info (`return_trigger` formatted label, `initiated_by`, `initiated_at` formatted date), Device Info (`serial_number`, `model` — show "N/A" if absent), Condition (`condition_assessment` badge, `reset_status` badge, `remarks`), Admin Evidence (photo gallery of `return_photo_urls` as clickable thumbnails, `admin_signature_url` as `<img>` — show "Not yet uploaded" if null), Employee Evidence (`user_signature_url` as `<img>` — show "Pending employee signature" if null), and Asset Status (`asset_status` badge).
3. WHEN `completed_at` is present, THE Return_Detail_Page SHALL additionally display a Completion section showing `completed_by`, `completed_at` formatted date, and `resolved_status` badge.
4. WHEN the user role is `it-admin` AND `asset_status` is `RETURN_PENDING` AND `admin_signature_url` is null, THE Return_Detail_Page SHALL render an "Upload Evidence" button that opens the Upload Evidence dialog (Requirement 2).
5. WHEN the user role is `it-admin` AND `asset_status` is `RETURN_PENDING` AND `admin_signature_url` is present AND `user_signature_url` is null, THE Return_Detail_Page SHALL render a "Re-notify Employee" button (Requirement 3).
6. WHEN the user role is `employee` AND `asset_status` is `RETURN_PENDING` AND `user_signature_url` is null, THE Return_Detail_Page SHALL render a "Sign & Complete Return" button that opens the Employee Signature dialog (Requirement 6).
7. IF the API returns a 403 error "You do not have access to this return record", THEN THE Return_Detail_Page SHALL display an inline `alert-danger` with the API message.
8. IF the API returns a 404 error, THEN THE Return_Detail_Page SHALL display an inline `alert-danger` with the API message.
9. THE Return_Detail_Page SHALL use `formatDate` from `src/lib/utils` for all date fields and semantic `Badge` variants for all status fields.
10. WHERE the user role is `management` or `finance`, THE Return_Detail_Page SHALL NOT be accessible (redirect to `/unauthorized`).
11. WHERE the user role is `employee` AND the employee is NOT the assigned user for the asset, THE Return_Detail_Page SHALL return a 403 from the API, which SHALL be displayed as an inline `alert-danger`.

---

### Requirement 5: Pending Signatures Dashboard (Employee)

**User Story:** As an Employee, I want to see a list of my pending signature tasks, so that I can quickly find and complete any outstanding return or handover signatures.

#### Acceptance Criteria

1. THE Pending_Signatures_Page SHALL be accessible from the main navigation for users with role `employee` only, and SHALL call `GET /users/me/pending-signatures` with `page` and `page_size` query parameters.
2. THE Pending_Signatures_Page SHALL display a DataTable with columns: Type (`document_type` badge — "Return" or "Handover"), Asset ID (link to the return or handover detail page), Return Trigger (`return_trigger` formatted label — return tasks only), Initiated At (`initiated_at` formatted date — return tasks only), and Actions ("View & Sign" button).
3. WHEN the Employee clicks "View & Sign" for a return task, THE Pending_Signatures_Page SHALL navigate to the Return Detail page for that `asset_id` and `record_id`.
4. WHEN the Employee clicks "View & Sign" for a handover task, THE Pending_Signatures_Page SHALL navigate to the Asset Detail page for that `asset_id`.
5. WHEN no pending signatures exist, THE Pending_Signatures_Page SHALL display the message "No pending signatures."
6. THE Pending_Signatures_Page SHALL support pagination via URL search params (`page`, `page_size`) synced with TanStack_Router `validateSearch`.
7. WHERE the user role is NOT `employee`, THE main navigation SHALL NOT render the "Pending Signatures" nav item, and the route SHALL redirect to `/unauthorized` via `beforeLoad`.

---

### Requirement 6: Employee Signature Upload (Employee)

**User Story:** As an Employee, I want to draw and upload my digital signature for a return, so that I can formally acknowledge the return of my assigned asset.

#### Acceptance Criteria

1. WHEN the Employee clicks "Sign & Complete Return" on the Return Detail page, THE Employee_Signature_Dialog SHALL open and display a read-only summary of the return (trigger, condition, remarks, device info) and a `Signature_Canvas` component with a "Clear" button.
2. WHEN the Employee submits the signature, THE Return_Process SHALL export the canvas as a PNG blob and call `POST /assets/{asset_id}/returns/{return_id}/signature-upload-url` with body `{ file_name: "user-signature.png" }`.
3. WHEN the presigned URL is returned, THE Return_Process SHALL upload the PNG blob to S3 via `PUT` with `Content-Type: image/png`.
4. WHEN the S3 upload succeeds, THE Return_Process SHALL store the returned `s3_key` and immediately proceed to Requirement 7 (Complete Return).
5. IF the S3 PUT request returns a 403 status, THEN THE Employee_Signature_Dialog SHALL show a `toast.error()` prompting the user to refresh and try again.
6. IF the API returns a 403 error "You are not assigned to this asset", THEN THE Return_Process SHALL show a `toast.error()` with the API message.
7. IF the API returns a 404 or 409 error, THEN THE Return_Process SHALL show a `toast.error()` with the API message.
8. WHERE the user role is NOT `employee`, THE "Sign & Complete Return" button SHALL NOT be rendered.

---

### Requirement 7: Complete Return (Employee)

**User Story:** As an Employee, I want to complete the return after uploading my signature, so that the asset is formally returned and my assignment is ended.

#### Acceptance Criteria

1. WHEN the employee signature has been successfully uploaded to S3, THE Return_Process SHALL call `PUT /assets/{asset_id}/returns/{return_id}/complete` with body `{ user_signature_s3_key: s3_key }`.
2. WHEN the `complete` call succeeds, THE Return_Process SHALL show a success toast "Return completed successfully.", close the dialog, and navigate the Employee away from the asset detail page (e.g. to their "My Assets" or dashboard page), since the asset is no longer assigned to them.
3. THE Return_Process SHALL support the following final asset status transitions based on `condition_assessment`: `GOOD` → `IN_STOCK`, `MINOR_DAMAGE` → `DAMAGED`, `MINOR_DAMAGE_REPAIR_REQUIRED` → `REPAIR_REQUIRED`, `MAJOR_DAMAGE` → `DISPOSAL_REVIEW`. The UI SHALL display the `new_status` from the response.
4. IF the API returns a 400 error (missing evidence), THEN THE Return_Process SHALL show a `toast.error()` with the API message.
5. IF the API returns a 403 error "You are not assigned to this asset", THEN THE Return_Process SHALL show a `toast.error()` with the API message.
6. IF the API returns a 404 or 409 error, THEN THE Return_Process SHALL show a `toast.error()` with the API message.
7. WHERE the user role is NOT `employee`, THE complete return action SHALL NOT be triggered.

---

### Requirement 8: List Returns for Asset (IT Admin)

**User Story:** As an IT Admin, I want to see all return records for a specific asset in a dedicated tab, so that I can track the full return history of that asset.

#### Acceptance Criteria

1. WHEN the user role is `it-admin`, THE Asset_Detail_Page SHALL render a "Returns" tab alongside the existing Software Requests and Issues tabs.
2. THE Returns_Tab SHALL call `GET /assets/{asset_id}/returns` with query params `page`, `page_size`, `return_trigger`, and `condition_assessment`, and SHALL display a DataTable with columns: Return Trigger (formatted label), Condition (colored badge), Reset Status (badge), Initiated By, Initiated At (formatted date), Status (`resolved_status` badge — show "Pending" if null), Completed At (formatted date — show "—" if null), and Actions (link to Return Detail).
3. THE Returns_Tab SHALL support pagination via URL search params prefixed to avoid collision with other tabs (e.g. `ret_page`).
4. THE Returns_Tab SHALL support filtering by `return_trigger` and `condition_assessment` via a filter Dialog following the filter-ui protocol (Filters button + Apply/Reset).
5. WHEN no returns exist for the asset, THE Returns_Tab SHALL display "No returns recorded for this asset."
6. WHERE the user role is NOT `it-admin`, THE Returns_Tab SHALL NOT be rendered on the Asset Detail page.

---

### Requirement 9: Pending Returns List (IT Admin)

**User Story:** As an IT Admin, I want to see a list of assets with approved replacement issues that are awaiting a return to be initiated, so that I can take action on them promptly.

#### Acceptance Criteria

1. THE Pending_Returns_Page SHALL be accessible from the main navigation for users with role `it-admin` only, and SHALL call `GET /assets/pending-returns` with `page` and `page_size` query parameters.
2. THE Pending_Returns_Page SHALL display a DataTable with columns: Asset ID (link to asset detail), Brand / Model (combined display), Serial Number (show "N/A" if null), Assigned To (`assignee_fullname`), Replacement Approved At (formatted date), Replacement Justification (truncated), Management Remarks (truncated), and Actions ("Initiate Return" button).
3. WHEN the IT_Admin clicks "Initiate Return" for a row, THE Pending_Returns_Page SHALL navigate to the Asset Detail page for that asset and open the Initiate Return dialog (Requirement 1).
4. WHEN no pending returns exist, THE Pending_Returns_Page SHALL display "No assets pending return."
5. THE Pending_Returns_Page SHALL support pagination via URL search params (`page`, `page_size`) synced with TanStack_Router `validateSearch`.
6. WHERE the user role is NOT `it-admin`, THE main navigation SHALL NOT render the "Pending Returns" nav item, and the route SHALL redirect to `/unauthorized` via `beforeLoad`.

---

### Requirement 10: Return Hooks and Query Keys

**User Story:** As a developer, I want all return-related API calls encapsulated in custom hooks with centralized query keys, so that cache invalidation is consistent and components remain free of direct API logic.

#### Acceptance Criteria

1. THE Return_Hooks module (`src/hooks/use-returns.ts`) SHALL export the following query hooks: `useReturnDetail(assetId, returnId)`, `useReturns(assetId, filters, page, pageSize)`, `usePendingReturns(page, pageSize)`, and `usePendingSignatures(page, pageSize)`.
2. THE Return_Hooks module SHALL export the following mutation hooks: `useInitiateReturn(assetId)`, `useGenerateReturnUploadUrls(assetId, returnId)`, `useSubmitAdminEvidence(assetId, returnId)`, `useGenerateReturnSignatureUploadUrl(assetId, returnId)`, and `useCompleteReturn(assetId, returnId)`.
3. THE `queryKeys` factory in `src/lib/query-keys.ts` SHALL be extended with a `returns` namespace containing keys for: `all()`, `list(assetId, filters)`, `detail(assetId, returnId)`, `pendingReturns(filters)`, and `pendingSignatures(filters)`.
4. ALL mutation hooks SHALL call `queryClient.invalidateQueries` in `onSettled` using the centralized query key factory — never raw string arrays.
5. THE `useInitiateReturn` mutation SHALL invalidate `queryKeys.assets.detail(assetId)` and `queryKeys.returns.list(assetId, {})` on settled.
6. THE `useCompleteReturn` mutation SHALL invalidate `queryKeys.assets.detail(assetId)` and `queryKeys.returns.detail(assetId, returnId)` on settled.
7. THE `useSubmitAdminEvidence` mutation SHALL invalidate `queryKeys.returns.detail(assetId, returnId)` on settled.
8. FOR ALL query hooks, THE Return_Hooks module SHALL configure `staleTime` of at least `60_000` ms to prevent over-fetching.

---

### Requirement 11: Return Permissions

**User Story:** As a developer, I want all return-related role and ownership checks centralized in the permissions module, so that conditional rendering is consistent and maintainable.

#### Acceptance Criteria

1. THE `src/lib/permissions.ts` module SHALL export a `getReturnDetailPermissions` function that accepts `{ role, currentUserId, initiatedById, assigneeUserId, assetStatus, adminSignatureUrl, userSignatureUrl }` and returns boolean flags: `canUploadEvidence`, `canRenotifyEmployee`, `canSignAndComplete`, `canViewReturnsTab`.
2. THE `canUploadEvidence` flag SHALL be `true` WHEN `role === "it-admin"` AND `assetStatus === "RETURN_PENDING"` AND `adminSignatureUrl` is null or undefined.
3. THE `canRenotifyEmployee` flag SHALL be `true` WHEN `role === "it-admin"` AND `assetStatus === "RETURN_PENDING"` AND `adminSignatureUrl` is present AND `userSignatureUrl` is null or undefined.
4. THE `canSignAndComplete` flag SHALL be `true` WHEN `role === "employee"` AND `assetStatus === "RETURN_PENDING"` AND `userSignatureUrl` is null or undefined.
5. THE `canViewReturnsTab` flag SHALL be `true` WHEN `role === "it-admin"`.
6. THE `getAssetDetailPermissions` function SHALL be extended to include a `showInitiateReturnButton` flag that is `true` WHEN `role === "it-admin"` AND `assetStatus === "ASSIGNED"`.
7. WHERE any permission flag is `false`, THE corresponding UI element SHALL NOT be rendered in any component.
