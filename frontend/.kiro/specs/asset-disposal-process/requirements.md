# Requirements Document

## Introduction

The Asset Disposal Process feature adds a complete disposal workflow to the Gadget Management System frontend. IT Admins initiate disposal requests for eligible assets, Management reviews and approves or rejects those requests, and IT Admins complete approved disposals by confirming data wipe and disposal date. Finance is notified automatically by the backend upon completion. The feature spans new routes, hooks, components, navigation items, and permission gates integrated into the existing React/TypeScript application.

## Glossary

- **Disposal_System**: The set of frontend components, hooks, routes, and permission logic that implement the asset disposal workflow.
- **IT_Admin**: A user with the `it-admin` role who initiates and completes disposal requests.
- **Management_User**: A user with the `management` role who reviews (approves or rejects) disposal requests.
- **Asset_Detail_Page**: The existing route at `/assets/$asset_id` that displays full asset information and action buttons.
- **Disposal_Detail_Page**: A new route at `/assets/$asset_id/disposals/$disposal_id` that displays disposal record details and conditional action buttons.
- **Disposals_List_Page**: A new route accessible from IT Admin navigation that lists all disposal records with filtering and pagination.
- **Pending_Disposals_Tab**: The "Disposals" tab on the existing Approvals page that lists pending disposal requests for Management review.
- **Initiate_Disposal_Dialog**: A modal dialog on the Asset Detail Page for IT Admin to submit a disposal request.
- **Complete_Disposal_Dialog**: A modal dialog on the Disposal Detail Page for IT Admin to finalize an approved disposal.
- **Management_Review_Dialog**: Modal dialogs on the Disposal Detail Page for Management to approve or reject a pending disposal.
- **Eligible_Asset**: An asset whose status is one of `DISPOSAL_REVIEW`, `IN_STOCK`, `DAMAGED`, or `REPAIR_REQUIRED`.
- **Locked_Disposal**: A disposal record where `is_locked` is `true`, indicating the asset is `DISPOSED` and immutable.
- **Disposal_Hook**: A custom React hook (`use-disposals.ts`) encapsulating all TanStack Query and Mutation calls for disposal API endpoints.
- **Query_Key_Factory**: The centralized `queryKeys` object in `query-keys.ts` used for cache key consistency.

## Requirements

### Requirement 1: Initiate Disposal Dialog

**User Story:** As an IT Admin, I want to initiate a disposal request for an eligible asset, so that the asset enters the disposal review workflow.

#### Acceptance Criteria

1. WHEN an IT_Admin views the Asset_Detail_Page for an Eligible_Asset, THE Disposal_System SHALL display an "Initiate Disposal" button in the Quick Actions card.
2. WHEN the IT_Admin clicks the "Initiate Disposal" button, THE Initiate_Disposal_Dialog SHALL open and display a read-only summary of the asset details (brand, model, serial number, cost, category).
3. THE Initiate_Disposal_Dialog SHALL contain a required "Disposal Reason" text input and a required "Justification" textarea, both validated as non-empty before submission.
4. WHEN the IT_Admin submits the Initiate_Disposal_Dialog with valid inputs, THE Disposal_System SHALL call `POST /assets/{asset_id}/disposals` with the `InitiateDisposalRequest` body.
5. WHEN the API returns a successful response, THE Disposal_System SHALL display a success toast "Disposal request submitted. Awaiting management approval.", close the dialog, and refresh the asset detail view.
6. IF the API returns a 400 validation error, THEN THE Disposal_System SHALL display the validation message in a toast.
7. IF the API returns a 404 error, THEN THE Disposal_System SHALL display "Asset not found" in a toast.
8. IF the API returns a 409 conflict error, THEN THE Disposal_System SHALL display "Asset is not in a valid status for disposal" in a toast.
9. WHILE the asset status is not one of `DISPOSAL_REVIEW`, `IN_STOCK`, `DAMAGED`, or `REPAIR_REQUIRED`, THE Disposal_System SHALL hide the "Initiate Disposal" button on the Asset_Detail_Page.
10. WHILE the user role is not `it-admin`, THE Disposal_System SHALL hide the "Initiate Disposal" button on the Asset_Detail_Page.

### Requirement 2: Pending Disposals Tab for Management

**User Story:** As a Management User, I want to see a list of pending disposal requests, so that I can review and act on them.

#### Acceptance Criteria

1. WHEN a Management_User navigates to the Approvals page, THE Pending_Disposals_Tab SHALL be visible and replace the existing placeholder content.
2. THE Pending_Disposals_Tab SHALL call `GET /disposals/pending` with `page` and `page_size` query parameters.
3. THE Pending_Disposals_Tab SHALL display a table with columns: Asset ID (link to Disposal_Detail_Page), Brand/Model (from `asset_specs`, showing "N/A" for null values), Serial Number (from `asset_specs`, showing "N/A" if null), Disposal Reason, Justification (truncated), Initiated By, Initiated At (formatted date), and a "Review" action button.
4. WHEN the Management_User clicks the "Review" action button for a row, THE Disposal_System SHALL navigate to the Disposal_Detail_Page for that asset and disposal.
5. THE Pending_Disposals_Tab SHALL include pagination controls that sync page state to URL search parameters.
6. WHEN no pending disposal requests exist, THE Pending_Disposals_Tab SHALL display "No pending disposal requests."
7. WHILE the user role is not `management`, THE Pending_Disposals_Tab SHALL remain hidden from the Approvals page tab list.

### Requirement 3: Disposal Detail Page

**User Story:** As an IT Admin or Management User, I want to view the full details of a disposal record, so that I can understand the disposal context and take appropriate action.

#### Acceptance Criteria

1. THE Disposal_System SHALL provide a route at `/assets/$asset_id/disposals/$disposal_id` accessible to users with `it-admin` or `management` roles.
2. THE Disposal_Detail_Page SHALL call `GET /assets/{asset_id}/disposals/{disposal_id}` and display: disposal reason, justification, initiated by, initiated at (formatted date).
3. THE Disposal_Detail_Page SHALL display asset specs: brand, model, serial number, product description, cost (formatted number), and purchase date (formatted date), showing "N/A" for null fields.
4. WHEN `management_reviewed_at` is present in the response, THE Disposal_Detail_Page SHALL display the Management Review section with: reviewed by, reviewed at (formatted date), remarks, and rejection reason.
5. WHEN `completed_at` is present in the response, THE Disposal_Detail_Page SHALL display the Completion section with: disposal date (formatted date), data wipe confirmed (badge), completed by, and completed at (formatted date).
6. WHEN `finance_notification_sent` is `true`, THE Disposal_Detail_Page SHALL display the Finance Notification section with: finance notification status (badge) and finance notified at (formatted date).
7. WHEN `is_locked` is `true`, THE Disposal_Detail_Page SHALL display a prominent banner "This asset has been disposed and is now locked. No further actions are allowed." and hide all action buttons.
8. IF a user without `it-admin` or `management` role navigates to the Disposal_Detail_Page, THEN THE Disposal_System SHALL redirect the user to the unauthorized page.
9. WHILE the Disposal_Detail_Page is loading data, THE Disposal_System SHALL display skeleton placeholders.
10. IF the API returns an error when loading disposal details, THEN THE Disposal_System SHALL display the error message inline.

### Requirement 4: Management Review Dialogs

**User Story:** As a Management User, I want to approve or reject a pending disposal request, so that the disposal workflow can proceed or be halted.

#### Acceptance Criteria

1. WHEN a Management_User views the Disposal_Detail_Page and the asset status is `DISPOSAL_PENDING`, THE Disposal_System SHALL display "Approve" and "Reject" action buttons.
2. WHEN the Management_User clicks "Approve", THE Management_Review_Dialog SHALL open with an optional "Remarks" textarea.
3. WHEN the Management_User confirms approval, THE Disposal_System SHALL call `PUT /assets/{asset_id}/disposals/{disposal_id}/management-review` with `decision: "APPROVE"` and optional `remarks`.
4. WHEN the approval API returns a successful response, THE Disposal_System SHALL display a success toast "Disposal request approved." and refresh the detail view.
5. WHEN the Management_User clicks "Reject", THE Management_Review_Dialog SHALL open with a required "Rejection Reason" textarea validated as non-empty.
6. WHEN the Management_User confirms rejection with a valid rejection reason, THE Disposal_System SHALL call `PUT /assets/{asset_id}/disposals/{disposal_id}/management-review` with `decision: "REJECT"` and `rejection_reason`.
7. WHEN the rejection API returns a successful response, THE Disposal_System SHALL display a success toast "Disposal request rejected." and refresh the detail view.
8. IF the API returns a 400 validation error, THEN THE Disposal_System SHALL display the validation message in a toast.
9. IF the API returns a 409 conflict error, THEN THE Disposal_System SHALL display "Disposal is not in DISPOSAL_PENDING status" in a toast.
10. WHILE the user role is not `management` or the asset status is not `DISPOSAL_PENDING`, THE Disposal_System SHALL hide the "Approve" and "Reject" buttons on the Disposal_Detail_Page.

### Requirement 5: Complete Disposal Dialog

**User Story:** As an IT Admin, I want to complete an approved disposal by confirming data wipe and providing a disposal date, so that the asset is marked as disposed and finance is notified.

#### Acceptance Criteria

1. WHEN an IT_Admin views the Disposal_Detail_Page and the asset status is `DISPOSAL_APPROVED`, THE Disposal_System SHALL display a "Complete Disposal" action button.
2. WHEN the IT_Admin clicks "Complete Disposal", THE Complete_Disposal_Dialog SHALL open with a required date picker for "Disposal Date" and a required "Data Wipe Confirmed" checkbox.
3. WHILE the "Data Wipe Confirmed" checkbox is unchecked, THE Complete_Disposal_Dialog SHALL disable the submit button and display an inline message "You must confirm that the device data has been wiped before completing the disposal."
4. WHEN the IT_Admin submits the Complete_Disposal_Dialog with a valid date and confirmed data wipe, THE Disposal_System SHALL call `PUT /assets/{asset_id}/disposals/{disposal_id}/complete` with the `CompleteDisposalRequest` body.
5. WHEN the API returns a successful response with `finance_notification_status` equal to `COMPLETED`, THE Disposal_System SHALL display a success toast "Disposal completed. Asset is now disposed." and an info toast "Finance team has been notified for asset write-off."
6. WHEN the API returns a successful response with `finance_notification_status` equal to `NO_FINANCE_USERS`, THE Disposal_System SHALL display a success toast and a warning toast "No finance users found. Finance notification could not be sent."
7. WHEN the API returns a successful response with `finance_notification_status` equal to `FAILED`, THE Disposal_System SHALL display a success toast and a warning toast "Finance notification failed. Please notify the finance team manually."
8. WHEN the completion succeeds, THE Disposal_System SHALL close the dialog and refresh the detail view, reflecting `DISPOSED` status and `is_locked` as `true`.
9. IF the API returns a 400 error with message "DataWipeConfirmed must be true to complete disposal", THEN THE Disposal_System SHALL display that message in a toast.
10. WHILE the user role is not `it-admin` or the asset status is not `DISPOSAL_APPROVED`, THE Disposal_System SHALL hide the "Complete Disposal" button on the Disposal_Detail_Page.

### Requirement 6: All Disposals List Page

**User Story:** As an IT Admin, I want to view a paginated, filterable list of all disposal records, so that I can track the status and history of asset disposals.

#### Acceptance Criteria

1. THE Disposal_System SHALL provide a "Disposals" navigation item visible only to users with the `it-admin` role, linking to a new route.
2. THE Disposals_List_Page SHALL call `GET /disposals` with `page`, `page_size`, and optional filter query parameters (`status`, `disposal_reason`, `date_from`, `date_to`).
3. THE Disposals_List_Page SHALL display a table with columns: Asset ID (link to Disposal_Detail_Page), Disposal Reason, Justification (truncated), Initiated By, Initiated At (formatted date), Status (colored badge), Reviewed By (showing "—" if null), Reviewed At (formatted date, showing "—" if null), Disposal Date (formatted date, showing "—" if null), and an actions column with a view detail link.
4. THE Disposals_List_Page SHALL include a filter dialog with: status dropdown (`DISPOSAL_PENDING`, `DISPOSAL_APPROVED`, `DISPOSAL_REJECTED`, `DISPOSED`, or "All"), disposal reason text input, and date range pickers for `date_from` and `date_to`.
5. THE Disposals_List_Page SHALL sync all filter and pagination state to URL search parameters via a Zod-validated search schema.
6. WHEN no disposal records match the current filters, THE Disposals_List_Page SHALL display "No disposal records found."
7. WHILE the user role is not `it-admin`, THE Disposal_System SHALL hide the "Disposals" navigation item and redirect unauthorized users accessing the route to the unauthorized page.

### Requirement 7: Disposal Hooks and Query Keys

**User Story:** As a developer, I want all disposal API interactions encapsulated in custom hooks with centralized query keys, so that the codebase follows established patterns for cache consistency and reusability.

#### Acceptance Criteria

1. THE Disposal_System SHALL provide a `use-disposals.ts` hook file containing custom hooks for: `useDisposalDetail`, `useDisposals`, `usePendingDisposals`, `useInitiateDisposal`, `useManagementReviewDisposal`, and `useCompleteDisposal`.
2. THE Disposal_Hook query hooks SHALL use query keys from the Query_Key_Factory (`queryKeys.disposals.*`).
3. THE Disposal_Hook mutation hooks SHALL invalidate relevant query keys in `onSettled` callbacks, including asset detail, disposal detail, disposal list, and pending disposals queries.
4. THE Query_Key_Factory SHALL be extended with a `disposals` namespace containing keys for `list`, `detail`, and `pendingDisposals`.

### Requirement 8: Disposal Permissions

**User Story:** As a developer, I want disposal-related permission checks centralized in the permissions module, so that role and status gating is consistent and maintainable.

#### Acceptance Criteria

1. THE Disposal_System SHALL extend `src/lib/permissions.ts` with a `getDisposalDetailPermissions` function that accepts role and asset status as context.
2. THE `getDisposalDetailPermissions` function SHALL return boolean flags: `canInitiateDisposal`, `canManagementReview`, `canCompleteDisposal`.
3. THE `canInitiateDisposal` flag SHALL be `true` only when the role is `it-admin` and the asset status is one of `DISPOSAL_REVIEW`, `IN_STOCK`, `DAMAGED`, or `REPAIR_REQUIRED`.
4. THE `canManagementReview` flag SHALL be `true` only when the role is `management` and the asset status is `DISPOSAL_PENDING`.
5. THE `canCompleteDisposal` flag SHALL be `true` only when the role is `it-admin` and the asset status is `DISPOSAL_APPROVED`.
6. THE `getAssetDetailPermissions` function SHALL be extended to include a `showInitiateDisposalButton` flag using the same eligibility logic as `canInitiateDisposal`.

### Requirement 9: Immutability Enforcement for Disposed Assets

**User Story:** As a user, I want disposed assets to be clearly marked as locked with all actions hidden, so that I cannot accidentally perform operations on immutable assets.

#### Acceptance Criteria

1. WHEN an asset's status is `DISPOSED`, THE Asset_Detail_Page SHALL display a prominent banner "This asset has been disposed and is locked. No further actions are permitted."
2. WHEN an asset's status is `DISPOSED`, THE Asset_Detail_Page SHALL hide all action buttons (assign, return, issue, software request, disposal, and any other actions).
3. WHEN `is_locked` is `true` on a disposal detail response, THE Disposal_Detail_Page SHALL hide all action buttons and display the lock banner.
4. THE Disposal_System SHALL display `DISPOSED` status as a neutral/gray badge in all list views.

### Requirement 10: Status Badge Colors for Disposal Flow

**User Story:** As a user, I want disposal-related statuses displayed with consistent color-coded badges, so that I can quickly identify the state of a disposal.

#### Acceptance Criteria

1. THE Disposal_System SHALL render `DISPOSAL_REVIEW` status with a warning-colored badge labeled "Disposal Review".
2. THE Disposal_System SHALL render `DISPOSAL_PENDING` status with a warning-colored badge labeled "Disposal Pending".
3. THE Disposal_System SHALL render `DISPOSAL_APPROVED` status with an info-colored badge labeled "Disposal Approved".
4. THE Disposal_System SHALL render `DISPOSAL_REJECTED` status with a danger-colored badge labeled "Disposal Rejected".
5. THE Disposal_System SHALL render `DISPOSED` status with a neutral/default-colored badge labeled "Disposed".
6. THE Disposal_System SHALL render finance notification status badges: `QUEUED` as warning, `COMPLETED` as success, `NO_FINANCE_USERS` as warning, `FAILED` as danger.
7. THE Disposal_System SHALL render data wipe confirmation badges: `true` as success labeled "Data Wipe Confirmed", `false` or null as danger labeled "Not Confirmed".
