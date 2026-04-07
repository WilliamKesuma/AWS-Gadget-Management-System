# Requirements Document

## Introduction

Phase 4 of the Gadget Management System adds Issue Management — a full lifecycle workflow for reporting, triaging, repairing, and replacing defective assets. Employees report issues on their assigned assets; IT Admins triage and drive resolution via repair or replacement; Management approves or rejects replacement requests. The feature spans a dedicated Maintenance Hub page, an Issue Detail page, a Pending Replacements dashboard, and action dialogs at each lifecycle step.

## Glossary

- **Issue**: A fault or defect record tied to a specific asset, identified by `asset_id` + `timestamp`.
- **Issue_System**: The frontend application responsible for issue management UI and API integration.
- **IssueStatus**: One of `TROUBLESHOOTING | UNDER_REPAIR | SEND_WARRANTY | RESOLVED | REPLACEMENT_REQUIRED | REPLACEMENT_APPROVED | REPLACEMENT_REJECTED`.
- **action_path**: A field on the issue record set to `"REPAIR"` or `"REPLACEMENT"` once the IT Admin chooses a resolution path from `TROUBLESHOOTING`.
- **Assigned_Employee**: The employee whose `user_id` matches the asset's `assignee.user_id`.
- **IT_Admin**: A user with role `it-admin`.
- **Management_User**: A user with role `management`.
- **Maintenance_Hub**: The `/maintenance` page listing issues with tabs for Requests, Ongoing Repairs, and Maintenance History.
- **Issue_Detail_Page**: The page at `/assets/{asset_id}/issues/{timestamp}` showing full issue information and role-appropriate action buttons.
- **Pending_Replacements_Page**: The management-only page listing all issues in `REPLACEMENT_REQUIRED` status.
- **Presigned_URL**: A time-limited S3 URL used to upload or view files without exposing credentials.
- **ApiError**: An error response from the backend with shape `{ message: string }`.

---

## Requirements

### Requirement 1: Submit Issue Report

**User Story:** As an Assigned_Employee, I want to report an issue on my assigned asset, so that IT Admin is notified and can begin resolution.

#### Acceptance Criteria

1. WHILE the current user's role is `employee` AND the asset status is `ASSIGNED` AND the current user is the Assigned_Employee, THE Issue_System SHALL render a "Report Issue" button on the Asset Detail page.
2. WHEN the "Report Issue" button is clicked, THE Issue_System SHALL open a modal dialog containing a required `issue_description` textarea field.
3. WHEN the submit form is submitted with a non-empty `issue_description`, THE Issue_System SHALL call `POST /assets/{asset_id}/issues` with the `SubmitIssueRequest` body.
4. WHEN the submission succeeds, THE Issue_System SHALL display a success toast: "Issue reported successfully. IT Admin has been notified.", close the modal, and invalidate the issues query for that asset.
5. IF the API returns a 400 error, THEN THE Issue_System SHALL display the error `message` field inline in the form.
6. IF the API returns a 403 error, THEN THE Issue_System SHALL display a `toast.error()` with the error `message` field.
7. IF the API returns a 409 error, THEN THE Issue_System SHALL display a `toast.error()` with the error `message` field.
8. THE Issue_System SHALL disable the submit button and show a loading indicator while the mutation is pending.

---

### Requirement 2: Upload Issue Evidence Photos

**User Story:** As an Assigned_Employee, I want to attach evidence photos to my issue report, so that IT Admin has visual context for the problem.

#### Acceptance Criteria

1. WHILE the current user's role is `employee` AND the current user is the Assigned_Employee, THE Issue_System SHALL render a drag-and-drop photo upload zone within the Submit Issue modal (as a second step after successful submission) or on the Issue Detail page.
2. WHEN the employee selects or drops one or more image files, THE Issue_System SHALL call `POST /assets/{asset_id}/issues/{timestamp}/upload-urls` with a `GenerateIssueUploadUrlsRequest` body listing each file with `type: "photo"`.
3. WHEN presigned URLs are returned, THE Issue_System SHALL upload each file directly to S3 via `PUT` with the file's `Content-Type` header.
4. WHEN all uploads succeed, THE Issue_System SHALL display a success toast: "Photos uploaded successfully."
5. IF any S3 `PUT` request fails, THEN THE Issue_System SHALL display a `toast.error()`: "One or more photo uploads failed. Please try again."
6. IF the API returns a 400 error on URL generation, THEN THE Issue_System SHALL display the error `message` field inline.
7. THE Issue_System SHALL accept only image files (JPEG, PNG) and reject other file types with an inline validation message.

---

### Requirement 3: Maintenance Hub Page — IT Admin View

**User Story:** As an IT_Admin, I want a central Maintenance Hub page listing all asset issues, so that I can triage and manage repairs across the organization.

#### Acceptance Criteria

1. THE Issue_System SHALL render the Maintenance Hub at route `/maintenance`, accessible only to users with role `it-admin` or `employee`; other roles SHALL be redirected to `/unauthorized`.
2. THE Issue_System SHALL display a page title "Maintenance Hub" and subtitle "Manage IT infrastructure maintenance and repair requests."
3. THE Issue_System SHALL display three stat cards: "Total Active Repairs", "Completed Today", and "Repairs Due Today", each derived from the issues data.
4. THE Issue_System SHALL render three tabs: "Requests", "Ongoing Repairs", and "Maintenance History", each with a count badge showing the number of items in that tab.
5. WHEN the "Requests" tab is active, THE Issue_System SHALL fetch issues filtered by `status=TROUBLESHOOTING` and display them as issue cards (not a table).
6. WHEN the "Ongoing Repairs" tab is active, THE Issue_System SHALL fetch issues with statuses `UNDER_REPAIR`, `SEND_WARRANTY`, `REPLACEMENT_REQUIRED`, `REPLACEMENT_APPROVED`, and `REPLACEMENT_REJECTED` and display them as issue cards.
7. WHEN the "Maintenance History" tab is active, THE Issue_System SHALL fetch issues filtered by `status=RESOLVED` and display them as issue cards.
8. THE Issue_System SHALL render each issue card with: a ticket ID derived from `asset_id` + truncated `timestamp`, the `issue_description` as the card title, a meta row showing `asset_id`, relative time since `created_at`, and `reported_by`, a status badge, and a "View Details" button linking to the Issue Detail page.
9. THE Issue_System SHALL render pagination controls below the card list showing "Showing X–Y of Z tickets".
10. IF a tab has no issues, THEN THE Issue_System SHALL display a contextual empty state message: "No issues reported." for Requests, "No ongoing repairs." for Ongoing Repairs, and "No maintenance history." for Maintenance History.
11. IF the issues query returns an error, THEN THE Issue_System SHALL display an inline `alert-danger` with the error message.
12. THE Issue_System SHALL sync the active tab and current page to URL search params so the state persists on refresh.

---

### Requirement 4: Maintenance Hub Page — Employee View

**User Story:** As an Assigned_Employee, I want to view my reported issues on the Maintenance Hub, so that I can track the status of my requests.

#### Acceptance Criteria

1. WHILE the current user's role is `employee`, THE Issue_System SHALL render the Maintenance Hub with page title "Requests" and subtitle "Track and manage your hardware applications and reported issues."
2. THE Issue_System SHALL display a "Report Issue" button (warning/orange variant) in the top-right area of the page header.
3. THE Issue_System SHALL display three stat cards: "Active Requests", "Pending Approval" (warning color), and "Resolved Monthly" (success color).
4. THE Issue_System SHALL render a table (using TanStack Table) with columns: Gadget/Service (asset icon + asset_id), Status (colored badge), Reported By, Date Submitted, and Actions (eye icon linking to Issue Detail).
5. THE Issue_System SHALL render tabs: "All Requests", "Pending", "In Review", "Approved", "Rejected" to filter the table by status groups.
6. THE Issue_System SHALL render pagination controls showing "Showing 1 to N of M requests" with Previous/Next buttons.
7. IF the issues query returns an error, THEN THE Issue_System SHALL display an inline `alert-danger` with the error message.

---

### Requirement 5: Issue Detail Page

**User Story:** As an IT_Admin, Management_User, or Assigned_Employee, I want to view the full details of an issue, so that I can understand its current state and take appropriate action.

#### Acceptance Criteria

1. THE Issue_System SHALL render the Issue Detail page at route `/assets/{asset_id}/issues/{timestamp}`, accessible to roles `it-admin`, `management`, and `employee` (employee only if Assigned_Employee); other roles SHALL be redirected to `/unauthorized`.
2. WHEN the page loads, THE Issue_System SHALL call `GET /assets/{asset_id}/issues/{timestamp}` and display the response.
3. THE Issue_System SHALL display an "Issue Info" section with `issue_description` and `action_path` (rendered as "Repair", "Replacement", or "Pending" if null).
4. THE Issue_System SHALL display an "Evidence Photos" section rendering `issue_photo_urls` as clickable thumbnails; IF the array is empty or null, THEN THE Issue_System SHALL display "No photos attached."
5. THE Issue_System SHALL display a "Status" section with the status badge, `created_at` (formatted via `formatDate`), and `reported_by`.
6. THE Issue_System SHALL display a "Triage" section with `triaged_by` and `triaged_at` only when those fields are populated.
7. WHEN `action_path` is `"REPAIR"`, THE Issue_System SHALL display a "Repair Details" section with `resolved_by`, `resolved_at`, `repair_notes`, `warranty_notes`, `warranty_sent_at`, `completed_at`, and `completion_notes` for any fields that are populated.
8. WHEN `action_path` is `"REPLACEMENT"`, THE Issue_System SHALL display a "Replacement Details" section with `replacement_justification`, `resolved_by`, and `resolved_at` for any fields that are populated.
9. THE Issue_System SHALL display a "Management Review" section with `management_reviewed_by`, `management_reviewed_at`, `management_rejection_reason`, and `management_remarks` only when those fields are populated.
10. IF the detail query returns an error, THEN THE Issue_System SHALL display an inline `alert-danger` with the error message.
11. WHILE the detail query is loading, THE Issue_System SHALL display a centered spinner.

---

### Requirement 6: Conditional Action Buttons on Issue Detail

**User Story:** As an IT_Admin or Management_User, I want to see only the action buttons relevant to the current issue status and my role, so that I can take the correct next step without confusion.

#### Acceptance Criteria

1. WHILE the current user's role is `it-admin` AND the issue status is `TROUBLESHOOTING`, THE Issue_System SHALL render a "Start Repair" button and a "Request Replacement" button on the Issue Detail page.
2. WHILE the current user's role is `it-admin` AND the issue status is `UNDER_REPAIR`, THE Issue_System SHALL render a "Send to Warranty" button and a "Complete Repair" button on the Issue Detail page.
3. WHILE the current user's role is `it-admin` AND the issue status is `SEND_WARRANTY`, THE Issue_System SHALL render a "Complete Repair" button on the Issue Detail page.
4. WHILE the current user's role is `management` AND the issue status is `REPLACEMENT_REQUIRED`, THE Issue_System SHALL render a "Review Replacement Request" button on the Issue Detail page.
5. THE Issue_System SHALL not render any action buttons for roles or statuses not listed in criteria 1–4.

---

### Requirement 7: Start Repair (Option A)

**User Story:** As an IT_Admin, I want to initiate a repair for a troubleshooting issue, so that the asset enters the repair workflow.

#### Acceptance Criteria

1. WHEN the "Start Repair" button is clicked, THE Issue_System SHALL open a modal dialog with an optional `repair_notes` textarea.
2. WHEN the form is submitted, THE Issue_System SHALL call `PUT /assets/{asset_id}/issues/{timestamp}/resolve-repair` with the `ResolveRepairRequest` body.
3. WHEN the mutation succeeds, THE Issue_System SHALL display a success toast: "Repair initiated. Status updated to Under Repair.", close the modal, and invalidate the issue detail query.
4. IF the API returns a 404 error, THEN THE Issue_System SHALL display a `toast.error()` with the error `message` field.
5. IF the API returns a 409 error, THEN THE Issue_System SHALL display a `toast.error()` with the error `message` field.
6. THE Issue_System SHALL disable the submit button while the mutation is pending.

---

### Requirement 8: Send to Warranty

**User Story:** As an IT_Admin, I want to send an asset under repair to warranty, so that the warranty claim process can begin.

#### Acceptance Criteria

1. WHEN the "Send to Warranty" button is clicked, THE Issue_System SHALL open a modal dialog with an optional `warranty_notes` textarea.
2. WHEN the form is submitted, THE Issue_System SHALL call `PUT /assets/{asset_id}/issues/{timestamp}/send-warranty` with the `SendWarrantyRequest` body.
3. WHEN the mutation succeeds, THE Issue_System SHALL display a success toast: "Asset sent to warranty.", close the modal, and invalidate the issue detail query.
4. IF the API returns a 404 error, THEN THE Issue_System SHALL display a `toast.error()` with the error `message` field.
5. IF the API returns a 409 error, THEN THE Issue_System SHALL display a `toast.error()` with the error `message` field.
6. THE Issue_System SHALL disable the submit button while the mutation is pending.

---

### Requirement 9: Complete Repair

**User Story:** As an IT_Admin, I want to mark a repair as complete, so that the asset is restored to Assigned status and the issue is resolved.

#### Acceptance Criteria

1. WHEN the "Complete Repair" button is clicked, THE Issue_System SHALL open a modal dialog with an optional `completion_notes` textarea.
2. WHEN the form is submitted, THE Issue_System SHALL call `PUT /assets/{asset_id}/issues/{timestamp}/complete-repair` with the `CompleteRepairRequest` body.
3. WHEN the mutation succeeds, THE Issue_System SHALL display a success toast: "Repair completed. Asset restored to Assigned status.", close the modal, and invalidate both the issue detail query and the asset detail query.
4. IF the API returns a 404 error, THEN THE Issue_System SHALL display a `toast.error()` with the error `message` field.
5. IF the API returns a 409 error, THEN THE Issue_System SHALL display a `toast.error()` with the error `message` field.
6. THE Issue_System SHALL disable the submit button while the mutation is pending.

---

### Requirement 10: Request Replacement (Option B)

**User Story:** As an IT_Admin, I want to request a replacement for an asset that cannot be repaired, so that Management can review and approve the replacement.

#### Acceptance Criteria

1. WHEN the "Request Replacement" button is clicked, THE Issue_System SHALL open a modal dialog with a required `replacement_justification` textarea.
2. THE Issue_System SHALL validate that `replacement_justification` is non-empty before enabling form submission.
3. WHEN the form is submitted with a valid justification, THE Issue_System SHALL call `PUT /assets/{asset_id}/issues/{timestamp}/request-replacement` with the `RequestReplacementRequest` body.
4. WHEN the mutation succeeds, THE Issue_System SHALL display a success toast: "Replacement request submitted. Management will review.", close the modal, and invalidate the issue detail query.
5. IF the API returns a 400 error, THEN THE Issue_System SHALL display the error `message` field inline in the form.
6. IF the API returns a 404 error, THEN THE Issue_System SHALL display a `toast.error()` with the error `message` field.
7. IF the API returns a 409 error, THEN THE Issue_System SHALL display a `toast.error()` with the error `message` field.
8. THE Issue_System SHALL disable the submit button while the mutation is pending.

---

### Requirement 11: Management Review of Replacement Request

**User Story:** As a Management_User, I want to approve or reject a replacement request, so that the appropriate next step in the asset lifecycle is triggered.

#### Acceptance Criteria

1. WHEN the "Review Replacement Request" button is clicked, THE Issue_System SHALL open a modal dialog with: a required `decision` radio group (`APPROVE` / `REJECT`), an optional `remarks` textarea, and a `rejection_reason` textarea that is required only when `decision` is `REJECT`.
2. WHEN the form is submitted with `decision = APPROVE`, THE Issue_System SHALL call `PUT /assets/{asset_id}/issues/{timestamp}/management-review` with `{ decision: "APPROVE", remarks }`.
3. WHEN the form is submitted with `decision = REJECT`, THE Issue_System SHALL call `PUT /assets/{asset_id}/issues/{timestamp}/management-review` with `{ decision: "REJECT", rejection_reason, remarks }`.
4. WHEN the mutation succeeds with `APPROVE`, THE Issue_System SHALL display a success toast: "Replacement approved.", close the modal, and invalidate the issue detail query and pending replacements query.
5. WHEN the mutation succeeds with `REJECT`, THE Issue_System SHALL display a success toast: "Replacement request rejected.", close the modal, and invalidate the issue detail query and pending replacements query.
6. IF the API returns a 400 error, THEN THE Issue_System SHALL display the error `message` field inline in the form.
7. IF the API returns a 404 error, THEN THE Issue_System SHALL display a `toast.error()` with the error `message` field.
8. IF the API returns a 409 error, THEN THE Issue_System SHALL display a `toast.error()` with the error `message` field.
9. THE Issue_System SHALL disable the submit button while the mutation is pending.
10. THE Issue_System SHALL validate that `rejection_reason` is non-empty when `decision` is `REJECT` before enabling form submission.

---

### Requirement 12: Pending Replacements Dashboard

**User Story:** As a Management_User, I want a dedicated page listing all pending replacement requests, so that I can review and act on them efficiently.

#### Acceptance Criteria

1. THE Issue_System SHALL render the Pending Replacements page at route `/pending-replacements`, accessible only to users with role `management`; other roles SHALL be redirected to `/unauthorized`.
2. WHEN the page loads, THE Issue_System SHALL call `GET /issues/pending-replacements` with `page` and `page_size` query params.
3. THE Issue_System SHALL render a table (using TanStack Table) with columns: Asset ID (linked to asset detail), Issue Description (truncated), Action Path, Replacement Justification (truncated), Reported By, Triaged By, Resolved By, Created At (formatted via `formatDate`), and Actions (eye icon linking to Issue Detail).
4. THE Issue_System SHALL render pagination controls below the table.
5. IF no pending replacements exist, THEN THE Issue_System SHALL display: "No pending replacement requests."
6. IF the query returns an error, THEN THE Issue_System SHALL display an inline `alert-danger` with the error message.
7. THE Issue_System SHALL sync `page` and `page_size` to URL search params via `validateSearch` with a Zod schema.

---

### Requirement 13: Issue Status Badge

**User Story:** As any user viewing issues, I want consistent color-coded status badges, so that I can quickly understand the state of any issue at a glance.

#### Acceptance Criteria

1. THE Issue_System SHALL render `TROUBLESHOOTING` status with a `warning` badge variant and label "Troubleshooting".
2. THE Issue_System SHALL render `UNDER_REPAIR` status with an `info` badge variant and label "Under Repair".
3. THE Issue_System SHALL render `SEND_WARRANTY` status with an `info` badge variant and label "Sent to Warranty".
4. THE Issue_System SHALL render `RESOLVED` status with a `success` badge variant and label "Resolved".
5. THE Issue_System SHALL render `REPLACEMENT_REQUIRED` status with a `warning` badge variant and label "Replacement Required".
6. THE Issue_System SHALL render `REPLACEMENT_APPROVED` status with a `success` badge variant and label "Replacement Approved".
7. THE Issue_System SHALL render `REPLACEMENT_REJECTED` status with a `danger` badge variant and label "Replacement Rejected".
8. THE Issue_System SHALL render `ISSUE_REPORTED` status with a `danger` badge variant and label "Issue Reported".

---

### Requirement 14: Query Key Factory and Custom Hooks

**User Story:** As a developer, I want all issue API calls encapsulated in custom hooks with a centralized query key factory, so that cache invalidation is consistent and components stay free of data-fetching logic.

#### Acceptance Criteria

1. THE Issue_System SHALL define an `issues` namespace in `src/lib/query-keys.ts` with keys for: `list(assetId, filters)`, `detail(assetId, timestamp)`, and `pendingReplacements(filters)`.
2. THE Issue_System SHALL implement all `useQuery` and `useMutation` calls in `src/hooks/use-issues.ts`; no component SHALL call `useQuery` or `useMutation` directly.
3. THE Issue_System SHALL set `staleTime: 60_000` on list queries and `staleTime: 5 * 60_000` on detail queries.
4. WHEN any issue mutation succeeds, THE Issue_System SHALL call `queryClient.invalidateQueries` using the factory keys — never raw string arrays.
5. THE Issue_System SHALL assign a `mutationKey` to every `useMutation` call in `use-issues.ts`.

---

### Requirement 15: Route Guards and SEO

**User Story:** As a developer, I want every new route to have proper access control and SEO metadata, so that unauthorized access is prevented and pages are correctly indexed.

#### Acceptance Criteria

1. THE Issue_System SHALL implement `beforeLoad` guards on all new routes using `context.userRole`; routes SHALL throw `redirect({ to: '/unauthorized' })` for disallowed roles.
2. THE Issue_System SHALL define a module-scope SEO constant (satisfying `SeoPageInput`) for each new route file.
3. THE Issue_System SHALL attach a `head` function to each route's options object that injects `noindex, nofollow` robots meta for all authenticated routes.
4. THE Issue_System SHALL never manually edit `routeTree.gen.ts`.
5. THE Issue_System SHALL use `validateSearch` with a Zod schema on any route that reads URL search params.
