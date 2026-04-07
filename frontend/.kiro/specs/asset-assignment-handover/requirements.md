# Requirements Document

## Introduction

This document specifies the frontend requirements for Phase 2 of the Gadget Management System: Asset Assignment & Handover. The feature enables IT Admins to assign IN_STOCK assets to employees, generates a formal handover PDF, and allows employees to review, sign, and accept the handover. All UI components are conditionally rendered based on the authenticated user's Cognito role. The backend API is fully implemented; this spec covers only the React/TypeScript frontend built with TanStack Router, TanStack Query, TanStack Form, and Shadcn UI.

## Glossary

- **Asset_Detail_Page**: The existing modal dialog route (`assets.$asset_id.tsx`) that displays full asset information including device metadata, invoice, and photos.
- **User_Detail_Page**: The existing users management page (`users.tsx`) that lists and manages organization users; will be extended with a per-employee signatures section.
- **Assignment_Modal**: A Shadcn Dialog opened from the Asset_Detail_Page that collects employee selection and optional notes to initiate an asset assignment.
- **Handover_Form**: A PDF document generated server-side during assignment containing asset details, IT Admin info, warranty data, and gadget photos. Accessed via presigned S3 URL.
- **Signature_Capture**: A UI component built with the `react-signature-canvas` library that allows an employee to draw a signature on a canvas or upload a signature image file (PNG).
- **Accept_Handover_Dialog**: A multi-step Shadcn Dialog guiding the assigned employee through reviewing the handover form, providing a signature, and accepting the asset.
- **Cancel_Assignment_Dialog**: A destructive confirmation Shadcn Dialog allowing IT Admins to cancel a pending assignment before the employee accepts.
- **Signatures_Section**: A table section on the User_Detail_Page displaying an employee's historical handover signatures with pagination and date filtering.
- **Pending_Handover**: A state where `assignment_date` is present on an asset and `status` is `IN_STOCK`, indicating the employee has not yet accepted.
- **Completed_Handover**: A state where `assignment_date` is present on an asset and `status` is `ASSIGNED`, indicating the employee has accepted.
- **IT_Admin**: A user with the `it-admin` Cognito role who manages asset lifecycle operations.
- **Employee**: A user with the `employee` Cognito role who receives and accepts assigned assets.
- **API_Client**: The centralized authenticated fetch wrapper in `src/lib/api-client.ts` that attaches Cognito ID tokens and parses error responses.
- **Query_Key_Factory**: The centralized query key definitions in `src/lib/query-keys.ts` used for TanStack Query cache management.

## Requirements

### Requirement 1: Assign Asset to Employee

**User Story:** As an IT Admin, I want to assign an IN_STOCK asset to an active employee, so that the system creates the assignment record, generates a handover PDF, and emails the employee in a single action.

#### Acceptance Criteria

1. WHILE the authenticated user role is `it-admin` AND the asset status is `IN_STOCK` AND no Pending_Handover exists, THE Asset_Detail_Page SHALL display an "Assign to Employee" button.
2. WHEN the IT_Admin clicks the "Assign to Employee" button, THE Asset_Detail_Page SHALL open the Assignment_Modal.
3. THE Assignment_Modal SHALL display a searchable employee selector populated from `GET /users?status=active&role=employee`.
4. THE Assignment_Modal SHALL display an optional "Notes" text field.
5. WHEN the IT_Admin confirms the assignment, THE Assignment_Modal SHALL send a `POST /assets/{asset_id}/assign` request with `{ employee_id, notes }` via the API_Client.
6. WHEN the API returns a successful response, THE Assignment_Modal SHALL display a success toast notification containing the assigned employee name and confirmation that the handover form was generated and email sent.
7. WHEN the API returns a successful response, THE Assignment_Modal SHALL offer to open the handover form PDF using the `presigned_url` from the response.
8. WHEN the API returns a successful response, THE Asset_Detail_Page SHALL invalidate the asset detail and asset list query caches to reflect the updated assignment state.
9. IF the API returns a 409 status with message indicating the asset is already assigned, THEN THE Assignment_Modal SHALL display the error message from the API response to the IT_Admin.
10. IF the API returns a 409 status with message indicating the asset is in progress to be assigned, THEN THE Assignment_Modal SHALL display the error message from the API response to the IT_Admin.
11. IF the API returns a 409 status with message indicating the asset must be in IN_STOCK status, THEN THE Assignment_Modal SHALL display the error message from the API response to the IT_Admin.
12. IF the API returns a 404 status with message indicating the employee was not found, THEN THE Assignment_Modal SHALL display the error message from the API response to the IT_Admin.
13. WHILE the assignment request is in progress, THE Assignment_Modal SHALL disable the confirm button and display a loading indicator.

### Requirement 2: View Handover Form PDF

**User Story:** As an IT Admin or the assigned employee, I want to view or download the handover form PDF, so that I can review the formal asset handover documentation.

#### Acceptance Criteria

1. WHILE the authenticated user role is `it-admin` AND the asset has a Pending_Handover or Completed_Handover, THE Asset_Detail_Page SHALL display a "View Handover Form" button.
2. WHILE the authenticated user role is `employee` AND the Employee is the assigned user for the asset AND the asset has a Pending_Handover or Completed_Handover, THE Asset_Detail_Page SHALL display a "View Handover Form" button.
3. WHEN the user clicks the "View Handover Form" button, THE Asset_Detail_Page SHALL send a `GET /assets/{asset_id}/assign-pdf-form` request via the API_Client.
4. WHEN the API returns a successful response with a `presigned_url`, THE Asset_Detail_Page SHALL open the PDF in a new browser tab.
5. IF the API returns a 404 status, THEN THE Asset_Detail_Page SHALL display the error message from the API response.
6. IF the API returns a 403 status, THEN THE Asset_Detail_Page SHALL display the error message from the API response.

### Requirement 3: Signature Upload and Accept Handover

**User Story:** As the assigned employee, I want to review the handover form, provide my signature, and accept the asset, so that the handover is formally completed and the asset status changes to ASSIGNED.

#### Acceptance Criteria

1. WHILE the authenticated user role is `employee` AND the Employee is the assigned user AND the asset status is `IN_STOCK` with a Pending_Handover, THE Asset_Detail_Page SHALL display an "Accept Asset" button.
2. WHEN the Employee clicks the "Accept Asset" button, THE Asset_Detail_Page SHALL open the Accept_Handover_Dialog.
3. THE Accept_Handover_Dialog SHALL display Step 1 containing asset details summary (brand, model, serial number, status), a "Download Handover Form" button, and a disabled checkbox labeled "I have read and reviewed the handover form".
4. WHEN the Employee clicks the "Download Handover Form" button in Step 1, THE Accept_Handover_Dialog SHALL call `GET /assets/{asset_id}/assign-pdf-form` and open the PDF in a new tab.
5. WHEN the Employee has viewed the handover form, THE Accept_Handover_Dialog SHALL enable the review checkbox in Step 1.
6. WHEN the Employee checks the review checkbox, THE Accept_Handover_Dialog SHALL enable navigation to Step 2.
7. THE Accept_Handover_Dialog SHALL display Step 2 containing the Signature_Capture component that supports both canvas-based drawing and file upload for PNG signature images.
8. WHEN the Employee provides a signature, THE Accept_Handover_Dialog SHALL call `POST /assets/{asset_id}/signature-upload-url` to obtain a presigned PUT URL and S3 key.
9. WHEN the presigned URL is obtained, THE Accept_Handover_Dialog SHALL upload the signature image directly to S3 using a PUT request with `Content-Type: image/png`.
10. WHEN the signature upload to S3 completes successfully, THE Accept_Handover_Dialog SHALL store the `s3_key` in component state and enable navigation to Step 3.
11. THE Accept_Handover_Dialog SHALL display Step 3 containing an "Agree & Accept Asset" confirmation button that is enabled only after the signature has been uploaded.
12. WHEN the Employee clicks "Agree & Accept Asset", THE Accept_Handover_Dialog SHALL send a `PUT /assets/{asset_id}/accept` request with `{ signature_s3_key }` via the API_Client.
13. WHEN the accept API returns a successful response, THE Accept_Handover_Dialog SHALL display a confirmation message with the `signed_form_url` from the response.
14. WHEN the accept API returns a successful response, THE Asset_Detail_Page SHALL invalidate the asset detail and asset list query caches so the status reflects `ASSIGNED`.
15. IF the accept API returns a 409 status with message about handover form not generated, THEN THE Accept_Handover_Dialog SHALL display the error message instructing the Employee to contact IT Admin.
16. IF the accept API returns a 409 status with message about asset state not allowing acceptance, THEN THE Accept_Handover_Dialog SHALL display the error message from the API response.
17. IF the accept API returns a 400 status with message about signature not found in S3, THEN THE Accept_Handover_Dialog SHALL display the error message and prompt the Employee to retry the signature upload.
18. WHILE any API request within the accept flow is in progress, THE Accept_Handover_Dialog SHALL disable action buttons and display a loading indicator.

### Requirement 4: Cancel Pending Assignment

**User Story:** As an IT Admin, I want to cancel a pending asset assignment before the employee accepts it, so that the asset returns to available IN_STOCK status.

#### Acceptance Criteria

1. WHILE the authenticated user role is `it-admin` AND the asset status is `IN_STOCK` AND a Pending_Handover exists, THE Asset_Detail_Page SHALL display a "Cancel Assignment" button styled as destructive.
2. WHEN the IT_Admin clicks the "Cancel Assignment" button, THE Asset_Detail_Page SHALL open the Cancel_Assignment_Dialog with a confirmation message: "Are you sure you want to cancel this assignment? The asset will return to IN_STOCK."
3. WHEN the IT_Admin confirms the cancellation, THE Cancel_Assignment_Dialog SHALL send a `DELETE /assets/{asset_id}/cancel-assignment` request via the API_Client.
4. WHEN the API returns a successful response, THE Cancel_Assignment_Dialog SHALL display a success toast notification and close the dialog.
5. WHEN the API returns a successful response, THE Asset_Detail_Page SHALL invalidate the asset detail and asset list query caches to reflect the cancelled assignment.
6. IF the API returns a 409 status with message indicating the employee has already accepted, THEN THE Cancel_Assignment_Dialog SHALL display the error message from the API response.
7. IF the API returns a 404 status with message indicating no pending assignment exists, THEN THE Cancel_Assignment_Dialog SHALL display the error message from the API response.
8. WHILE the cancellation request is in progress, THE Cancel_Assignment_Dialog SHALL disable the confirm and cancel buttons and display a loading indicator.

### Requirement 5: Employee Signatures List

**User Story:** As an IT Admin, I want to view an employee's historical handover signatures, so that I can audit past asset assignments and verify signature records.

#### Acceptance Criteria

1. WHILE the authenticated user role is `it-admin`, THE User_Detail_Page SHALL display a "Handover Signatures" section for employee users.
2. THE Signatures_Section SHALL call `GET /users/{employee_id}/signatures` with `page`, `page_size`, `sort_order`, `assignment_date_from`, and `assignment_date_to` query parameters.
3. THE Signatures_Section SHALL display a table with columns: Asset ID (linked to asset detail), Brand, Model, Assignment Date (formatted via `formatDate`), Signed At (formatted via `formatDate`), and Signature (clickable thumbnail opening the signature image).
4. THE Signatures_Section SHALL provide pagination controls matching the paginated API response shape.
5. THE Signatures_Section SHALL provide date range filter inputs for `assignment_date_from` and `assignment_date_to`.
6. WHEN no signatures exist for the employee, THE Signatures_Section SHALL display the message "No handover signatures on record."
7. THE Signatures_Section SHALL use the Query_Key_Factory for cache key management of signature list queries.

### Requirement 6: Pending Handover Detection

**User Story:** As a frontend developer, I want a consistent mechanism to detect pending and completed handovers, so that conditional rendering logic across the Asset_Detail_Page is reliable.

#### Acceptance Criteria

1. WHEN an asset has `assignment_date` present AND `status` is `IN_STOCK`, THE Asset_Detail_Page SHALL treat the asset as having a Pending_Handover.
2. WHEN an asset has `assignment_date` present AND `status` is `ASSIGNED`, THE Asset_Detail_Page SHALL treat the asset as having a Completed_Handover.
3. WHEN an asset has no `assignment_date` AND `status` is `IN_STOCK`, THE Asset_Detail_Page SHALL treat the asset as available for assignment.
4. THE Asset_Detail_Page SHALL use the `assignment_date` field from the asset list response passed via route state or context to determine handover status on the detail view.

### Requirement 7: Conditional Action Button Rendering

**User Story:** As a user of any role, I want to see only the action buttons relevant to my role and the asset's current state, so that the interface is clear and prevents unauthorized actions.

#### Acceptance Criteria

1. THE asset list table SHALL render a maximum of two buttons per row: a "View Details" button/link and a dropdown menu (⋯) button containing all other actions.
2. THE dropdown menu items SHALL be conditionally rendered based on the user's role and the asset's current status and handover state.
3. IF no dropdown actions are available for the current user/role/state combination, THEN THE dropdown menu trigger SHALL be hidden and only the "View Details" button SHALL be displayed.
4. WHILE the user role is `it-admin` AND asset status is `IN_STOCK` AND no Pending_Handover exists, THE dropdown menu SHALL include an "Assign to Employee" item.
5. WHILE the user role is `it-admin` AND asset status is `IN_STOCK` AND a Pending_Handover exists, THE dropdown menu SHALL include "View Handover Form" and "Cancel Assignment" items.
6. WHILE the user role is `it-admin` AND asset status is `ASSIGNED`, THE dropdown menu SHALL include a "View Handover Form" item.
7. WHILE the user role is `employee` AND the Employee is the assigned user AND asset status is `IN_STOCK` AND a Pending_Handover exists, THE dropdown menu SHALL include "View Handover Form" and "Accept Asset" items.
8. WHILE the user role is `employee` AND the Employee is the assigned user AND asset status is `ASSIGNED`, THE dropdown menu SHALL include a "View Handover Form" item.
9. WHILE the user role is `management` or `finance`, THE dropdown menu SHALL not include any assignment or handover action items.
10. ON the Asset_Detail_Page, THE same conditional action buttons SHALL be rendered based on role and asset state, following the same visibility rules as the dropdown menu items.

### Requirement 8: Assignment API Hooks and Type Definitions

**User Story:** As a frontend developer, I want dedicated TanStack Query hooks and TypeScript types for all assignment and handover API endpoints, so that the feature integrates consistently with the existing codebase patterns.

#### Acceptance Criteria

1. THE API_Client layer SHALL define TypeScript types for `AssignAssetRequest`, `AssignAssetResponse`, `CancelAssignmentResponse`, `GetHandoverFormResponse`, `GenerateSignatureUploadUrlResponse`, `AcceptHandoverRequest`, `AcceptHandoverResponse`, and `SignatureItem`.
2. THE existing `src/hooks/use-assets.ts` file SHALL be extended with a `useAssignAsset` mutation hook that calls `POST /assets/{asset_id}/assign` and invalidates asset query caches on settlement.
3. THE existing `src/hooks/use-assets.ts` file SHALL be extended with a `useCancelAssignment` mutation hook that calls `DELETE /assets/{asset_id}/cancel-assignment` and invalidates asset query caches on settlement.
4. THE existing `src/hooks/use-assets.ts` file SHALL be extended with a `useAcceptHandover` mutation hook that calls `PUT /assets/{asset_id}/accept` and invalidates asset query caches on settlement.
5. THE existing `src/hooks/use-assets.ts` file SHALL be extended with a `useHandoverForm` query or mutation hook that calls `GET /assets/{asset_id}/assign-pdf-form`.
6. THE existing `src/hooks/use-assets.ts` file SHALL be extended with a `useSignatureUploadUrl` mutation hook that calls `POST /assets/{asset_id}/signature-upload-url`.
7. THE existing `src/hooks/use-assets.ts` file SHALL be extended with a `useEmployeeSignatures` query hook that calls `GET /users/{employee_id}/signatures` with pagination and date filter parameters.
8. THE Query_Key_Factory SHALL be extended with keys for handover form, employee signatures, and assignment-related queries.

### Requirement 9: Route Access Control for Employee Asset Detail

**User Story:** As an employee, I want to access the Asset Detail page for assets assigned to me, so that I can view details and complete the handover acceptance flow.

#### Acceptance Criteria

1. THE Asset_Detail_Page route guard SHALL allow access for users with the `employee` role in addition to `it-admin` and `management`.
2. WHILE the user role is `employee`, THE Asset_Detail_Page SHALL display asset information in read-only mode without management-specific actions (approve/reject).
3. THE Asset_Detail_Page SHALL use the authenticated user's identity to determine if the Employee is the assigned user for conditional button rendering.

### Requirement 10: Error Handling for Expired Presigned URLs

**User Story:** As a user viewing handover documents or uploading signatures, I want clear feedback when a presigned URL has expired, so that I can refresh and retry the operation.

#### Acceptance Criteria

1. IF a fetch to a presigned S3 URL returns a 403 status, THEN THE requesting component SHALL display a message indicating the URL has expired and prompt the user to refresh.
2. WHEN the user requests a refresh after a presigned URL expiry, THE requesting component SHALL re-fetch the presigned URL from the appropriate API endpoint.
