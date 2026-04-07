# Requirements Document

## Introduction

This feature implements the Asset Creation Flow (Phase 1) for the Gadget Management System frontend. It covers a 4-step process for IT Admins to upload invoice/photo files and wait for an AI scan (Steps 1–2, handled inside a modal dialog on the Asset List page), then review and confirm extracted fields (Step 3, full page), and receive a success confirmation (Step 4, full page). It also includes an Asset List page with pagination and status filtering, and an Approve/Reject page restricted to Management users. All routing uses TanStack Router with URL search params as the source of truth for full-page step state. Steps 1 and 2 are modal-based and do not use URL params.

## Glossary

- **Upload_Modal**: A dialog component rendered on top of the `Asset_List_Page` at `/assets`. It contains both the `Upload_Step` (file selection) and the `Polling_Step` (scan progress), transitioning between them inline without a route change.
- **Upload_Step**: Step 1 of the flow — file selection via drag-and-drop zones and upload to S3 via presigned URLs. Rendered inside `Upload_Modal`.
- **Polling_Step**: Step 2 of the flow — polls the scan job until it completes or fails, showing an animated 3-step progress list. Rendered inside `Upload_Modal`.
- **Confirm_Step**: Step 3 of the flow — form pre-filled from extracted fields for IT Admin review and submission. Rendered as a full page at `/assets/new?upload_session_id=&scan_job_id=&ready=1`.
- **Success_Step**: Step 4 of the flow — confirmation screen shown after asset creation. Rendered as a full page at `/assets/new?asset_id=`.
- **Asset_Creation_Wizard**: The component rendered at `/assets/new` that detects the current step from URL search params and renders either `Confirm_Step` or `Success_Step`.
- **Asset_List_Page**: The `/assets` route displaying a paginated, filterable table of assets, and hosting the `Upload_Modal`.
- **Approve_Page**: The `/assets/:asset_id/approve` route for Management users to approve or reject a pending asset.
- **Scan_Job**: A backend job that processes uploaded files and extracts asset field values.
- **Extracted_Field**: A `ExtractedFieldValue` object containing `value`, `confidence`, `alternative_value`, and `alternative_confidence`.
- **Presigned_URL**: A time-limited S3 URL used to upload a file directly without auth headers.
- **Drag_Drop_Zone**: A file input area that accepts files via click or drag-and-drop, displaying file name, size, and status once a file is selected.
- **IT_Admin**: A user with the `it-admin` Cognito role.
- **Management_User**: A user with the `management` Cognito role.
- **API_Client**: The `apiClient` function in `src/lib/api-client.ts` that attaches the Cognito JWT Bearer token to all requests.
- **Router_Context**: The TanStack Router context object carrying `queryClient` and `userRole` from `_authenticated.tsx` `beforeLoad`.

---

## Requirements

### Requirement 1: Step Detection and Route Structure

**User Story:** As an IT Admin, I want the app to route me to the correct step based on URL params so that I can bookmark or refresh full-page steps without losing my place.

#### Acceptance Criteria

1. WHEN the `/assets/new` route has `upload_session_id`, `scan_job_id`, and `ready=1` search params, THE `Asset_Creation_Wizard` SHALL render `Confirm_Step`.
2. WHEN the `/assets/new` route has an `asset_id` search param, THE `Asset_Creation_Wizard` SHALL render `Success_Step`.
3. WHEN the `/assets/new` route has no search params, or has only `upload_session_id` and `scan_job_id` without `ready=1`, THE `Asset_Creation_Wizard` SHALL redirect to `/assets`.
4. THE `/assets/new` route SHALL validate all search params using a Zod schema passed to `validateSearch` in the route definition.
5. THE `/assets/:asset_id/approve` route SHALL define `asset_id` as a path param validated by TanStack Router.
6. THE `Asset_List_Page` at `/assets` SHALL manage the open/closed state of `Upload_Modal` as local component state, not as a URL param.

---

### Requirement 2: Upload Modal — Open/Close Behavior

**User Story:** As an IT Admin, I want to open an upload dialog from the Asset List page so that I can start the asset creation process without leaving the list.

#### Acceptance Criteria

1. THE `Asset_List_Page` SHALL render an "Add New Asset" button that opens the `Upload_Modal` when clicked.
2. WHEN the `Upload_Modal` is open and the user clicks the X button, THE `Upload_Modal` SHALL close and any in-progress upload or polling SHALL be aborted.
3. WHEN the `Upload_Modal` is open and the user clicks the "Cancel" button, THE `Upload_Modal` SHALL close and any in-progress upload or polling SHALL be aborted.
4. WHILE uploads or polling are in progress, THE `Upload_Modal` SHALL remain open until the user explicitly cancels or the process completes.
5. WHEN polling completes with `status` equal to `"COMPLETED"`, THE `Upload_Modal` SHALL close and THE `Asset_List_Page` SHALL navigate to `/assets/new?upload_session_id={upload_session_id}&scan_job_id={scan_job_id}&ready=1`.
6. WHEN polling completes with `status` equal to `"SCAN_FAILED"`, THE `Upload_Modal` SHALL remain open and display an error state.

---

### Requirement 3: Upload Step — File Selection and Validation

**User Story:** As an IT Admin, I want to select an invoice and gadget photos using drag-and-drop zones so that I can catch file errors before hitting the API.

#### Acceptance Criteria

1. THE `Upload_Step` SHALL render a `Drag_Drop_Zone` for the invoice accepting `application/pdf` and `image/*` MIME types, limited to exactly 1 file, labelled "Invoice (PDF or Image)".
2. THE `Upload_Step` SHALL render a `Drag_Drop_Zone` for gadget photos accepting `image/*` MIME types, accepting between 1 and 5 files, labelled "Asset Photos (Up to 5)".
3. WHEN a file is selected in a `Drag_Drop_Zone`, THE `Upload_Step` SHALL display the file name, file size, and a "Ready to process" status label within the zone.
4. THE `Upload_Step` SHALL render a "UPLOADED FILES" list below the drop zones showing each selected file with its file icon, name, size, "Ready to process" status, and a trash/delete icon.
5. WHEN the user clicks the trash icon for a file, THE `Upload_Step` SHALL remove that file from the selection.
6. WHEN the user submits with no invoice file selected, THE `Upload_Step` SHALL display an inline validation error without calling the API.
7. WHEN the user submits with more than 5 gadget photo files selected, THE `Upload_Step` SHALL display an inline validation error without calling the API.
8. WHEN the user submits with zero gadget photo files selected, THE `Upload_Step` SHALL display an inline validation error without calling the API.
9. WHEN the user submits with a file whose MIME type does not match the accepted types, THE `Upload_Step` SHALL display an inline validation error without calling the API.
10. THE `Upload_Step` SHALL render a "Cancel" button (outlined, destructive style) and an "Upload & Scan" button (filled, primary style) in the modal footer.

---

### Requirement 4: Upload Step — API Call and S3 Upload

**User Story:** As an IT Admin, I want my files uploaded to S3 via presigned URLs so that the backend can scan them without handling the binary data directly.

#### Acceptance Criteria

1. WHEN the user clicks "Upload & Scan" with valid files, THE `Upload_Step` SHALL call `POST /assets/uploads` via `API_Client` with a `GenerateUploadUrlsRequest` body containing a `files` array of `FileManifestItem` objects derived from the selected files.
2. WHEN `POST /assets/uploads` returns a `GenerateUploadUrlsResponse`, THE `Upload_Step` SHALL perform a `PUT` request to each `presigned_url` in `response.urls` with the matching file as the request body and the file's `content_type` as the `Content-Type` header.
3. THE `Upload_Step` SHALL NOT include an `Authorization` header in the presigned URL `PUT` requests.
4. WHEN all `PUT` requests complete successfully, THE `Upload_Modal` SHALL transition from `Upload_Step` to `Polling_Step` without closing the modal.
5. IF `POST /assets/uploads` returns an error, THEN THE `Upload_Step` SHALL display the API error message inline and SHALL NOT proceed to S3 uploads.
6. IF any presigned URL `PUT` request fails, THEN THE `Upload_Step` SHALL display an error message and SHALL NOT transition to `Polling_Step`.
7. WHILE uploads are in progress, THE `Upload_Step` SHALL disable the "Upload & Scan" button and show a loading indicator.

---

### Requirement 5: Polling Step — Scan Job Polling

**User Story:** As an IT Admin, I want the modal to automatically poll the scan job and show progress so that I can see the AI extraction status without manually refreshing.

#### Acceptance Criteria

1. WHEN `Polling_Step` mounts inside `Upload_Modal`, THE `Polling_Step` SHALL begin polling `GET /assets/scan/{scan_job_id}` every 3 seconds using the `scan_job_id` returned from the upload API response.
2. THE `Polling_Step` SHALL display the title "Extracting Data..." and a centered circular spinner with a sparkles icon inside.
3. THE `Polling_Step` SHALL display the text "Our AI is analyzing your documents to pre-fill the asset details."
4. THE `Polling_Step` SHALL render an "EXTRACTION PROGRESS" card containing three animated steps: "Analyzing Invoice", "Processing Photos", and "Validating Serial Numbers".
5. WHILE polling is in progress, THE `Polling_Step` SHALL animate the three progress steps through Pending (grey clock icon), In Progress (blue spinner), and Completed (green checkmark) states to provide visual feedback.
6. THE animated progress step states SHALL be cosmetic only — the actual completion is determined solely by the `GET /assets/scan/{scan_job_id}` response `status` field.
7. WHEN `GetScanResultsResponse.status` equals `"COMPLETED"`, THE `Polling_Step` SHALL stop polling and pass `extracted_fields` via TanStack Router navigation state when navigating to the `Confirm_Step` URL.
8. WHEN `GetScanResultsResponse.status` equals `"SCAN_FAILED"`, THE `Polling_Step` SHALL stop polling and display the `failure_reason` as an error message within the modal.
9. WHEN `Polling_Step` unmounts, THE `Polling_Step` SHALL clear the polling interval to prevent memory leaks.
10. IF a polling request returns a network or API error, THEN THE `Polling_Step` SHALL display an error message and stop polling.
11. THE `Polling_Step` SHALL render a "Cancel" button (outlined, destructive style, full width) in the modal footer.

---

### Requirement 6: Confirm Step — Form Pre-fill and Confidence Display

**User Story:** As an IT Admin, I want the form pre-filled from extracted fields with confidence indicators so that I can quickly review and correct AI-extracted data.

#### Acceptance Criteria

1. WHEN `Confirm_Step` mounts, THE `Confirm_Step` SHALL read `extracted_fields` from TanStack Router navigation state and pre-fill the corresponding form fields.
2. THE `Confirm_Step` SHALL render a `category` dropdown with options `LAPTOP`, `MOBILE_PHONE`, `TABLET`, and `OTHERS`.
3. THE `Confirm_Step` SHALL render text inputs for `procurement_id` and `requestor`, and a number input for `approved_budget`, with no pre-fill from extracted fields.
4. THE `Confirm_Step` SHALL pre-fill `invoice_number`, `vendor`, `purchase_date`, `brand`, `model_name`, `cost`, `serial_number`, `product_description`, and `payment_method` from the corresponding `extracted_fields` values.
5. WHEN an extracted field has `confidence` less than `0.8`, THE `Confirm_Step` SHALL apply a yellow border style to that field's input.
6. THE `Confirm_Step` SHALL display the confidence score as a percentage label adjacent to each pre-filled field (e.g. "85% confidence").
7. WHEN an extracted field has a non-empty `alternative_value`, THE `Confirm_Step` SHALL display it as a hint below the field in the format "Alternative: {alternative_value}".
8. THE `Confirm_Step` SHALL validate all required fields using a Zod schema via `@tanstack/zod-form-adapter` before allowing submission.

---

### Requirement 7: Confirm Step — Asset Creation Submission

**User Story:** As an IT Admin, I want to submit the confirmed form to create the asset so that it enters the approval workflow.

#### Acceptance Criteria

1. WHEN the user submits the `Confirm_Step` form with valid data, THE `Confirm_Step` SHALL call `POST /assets` via `API_Client` with a `CreateAssetRequest` body that includes `scan_job_id` from the URL search param.
2. WHEN `POST /assets` returns a `CreateAssetResponse`, THE `Confirm_Step` SHALL navigate to `/assets/new?asset_id={asset_id}`.
3. IF `POST /assets` returns an error, THEN THE `Confirm_Step` SHALL display the API error message and SHALL NOT navigate.
4. WHILE the form is submitting, THE `Confirm_Step` SHALL disable the submit button via `form.state.isSubmitting`.

---

### Requirement 8: Success Step

**User Story:** As an IT Admin, I want a clear confirmation screen after asset creation so that I know the asset was submitted for approval.

#### Acceptance Criteria

1. WHEN `Success_Step` renders, THE `Success_Step` SHALL display the message "Asset {asset_id} created and pending management approval." where `asset_id` is read from the URL search param.
2. THE `Success_Step` SHALL render a "Create Another Asset" button that navigates to `/assets` and opens the `Upload_Modal`.
3. THE `Success_Step` SHALL render a "View Asset List" button that navigates to `/assets`.

---

### Requirement 9: Asset List Page — Data Fetching and Display

**User Story:** As an IT Admin or Management user, I want to see a paginated table of all assets so that I can monitor inventory status.

#### Acceptance Criteria

1. WHEN `Asset_List_Page` mounts, THE `Asset_List_Page` SHALL call `GET /assets` via `API_Client` with `page` and `page_size` query params derived from the URL search params.
2. THE `Asset_List_Page` SHALL display a table with columns: Asset ID, Brand, Model, Serial Number, Status, and Assignment Date.
3. THE `Asset_List_Page` SHALL render pagination controls using `current_page`, `total_pages`, and `total_items` from the `ListAssetsResponse`.
4. WHEN the user clicks a page number, THE `Asset_List_Page` SHALL update the `page` URL search param.
5. THE `Asset_List_Page` SHALL render a status filter dropdown containing all `AssetStatus` values.
6. WHEN the user selects a status filter, THE `Asset_List_Page` SHALL update the `status` URL search param and reset `page` to `1`.
7. WHEN `Asset_List_Page` is loading, THE `Asset_List_Page` SHALL display a loading state.
8. WHEN `Asset_List_Page` has no results, THE `Asset_List_Page` SHALL display an empty state message.
9. IF `GET /assets` returns an error, THEN THE `Asset_List_Page` SHALL display an error message.
10. WHEN the user clicks a row where `status` equals `"ASSET_PENDING_APPROVAL"`, THE `Asset_List_Page` SHALL navigate to `/assets/{asset_id}/approve`.

---

### Requirement 10: Approve/Reject Page — Access Control

**User Story:** As a Management user, I want the approve/reject page to be restricted to my role so that only authorized users can take approval actions.

#### Acceptance Criteria

1. THE `/assets/:asset_id/approve` route SHALL use `beforeLoad` to read `context.userRole` from `Router_Context`.
2. WHEN `context.userRole` is not `"management"`, THE `Approve_Page` route SHALL throw a redirect to `/unauthorized`.

---

### Requirement 11: Approve/Reject Page — Approve and Reject Actions

**User Story:** As a Management user, I want to approve or reject a pending asset with optional remarks so that the asset lifecycle can proceed.

#### Acceptance Criteria

1. WHEN `Approve_Page` renders, THE `Approve_Page` SHALL display the `asset_id` prominently.
2. THE `Approve_Page` SHALL render an "Approve" button and a "Reject" button.
3. WHEN the user clicks "Approve", THE `Approve_Page` SHALL show an optional remarks textarea before the user confirms the action.
4. WHEN the user clicks "Reject", THE `Approve_Page` SHALL show a required rejection reason textarea.
5. WHILE the rejection reason textarea is empty, THE `Approve_Page` SHALL disable the reject confirm button.
6. WHEN the user confirms an approve action, THE `Approve_Page` SHALL call `PUT /assets/{asset_id}/approve` via `API_Client` with `ApproveAssetRequest` body `{ action: "APPROVE", remarks }`.
7. WHEN the user confirms a reject action, THE `Approve_Page` SHALL call `PUT /assets/{asset_id}/approve` via `API_Client` with `ApproveAssetRequest` body `{ action: "REJECT", rejection_reason }`.
8. WHEN `PUT /assets/{asset_id}/approve` returns an `ApproveAssetResponse`, THE `Approve_Page` SHALL display the new `status` value.
9. WHEN the action succeeds, THE `Approve_Page` SHALL render a "Back to List" button that navigates to `/assets`.
10. IF `PUT /assets/{asset_id}/approve` returns an error, THEN THE `Approve_Page` SHALL display the API error message.

---

### Requirement 12: Authentication and Authorization on All API Calls

**User Story:** As a system, I want every API call to include a valid Cognito JWT so that the backend can authenticate and authorize requests.

#### Acceptance Criteria

1. THE `API_Client` SHALL attach the Cognito ID token as `Authorization: Bearer {token}` on every request to the backend API.
2. THE `API_Client` SHALL read the base URL from the `VITE_API_BASE_URL` environment variable.
3. IF the Cognito session is unavailable, THEN THE `API_Client` SHALL send the request without an `Authorization` header rather than throwing before the request is made.

---

### Requirement 13: SEO and Route Head Metadata

**User Story:** As a developer, I want every route to declare head metadata so that the app meets SEO and crawl policy requirements.

#### Acceptance Criteria

1. THE `/assets/new` route SHALL declare a `head` function that sets `title`, `description`, and `robots: noindex, nofollow`.
2. THE `/assets` route SHALL declare a `head` function that sets `title`, `description`, and `robots: noindex, nofollow`.
3. THE `/assets/:asset_id/approve` route SHALL declare a `head` function that sets `title`, `description`, and `robots: noindex, nofollow`.
4. THE SEO constants for each route SHALL be defined at module scope using the `satisfies SeoPageInput` pattern.
