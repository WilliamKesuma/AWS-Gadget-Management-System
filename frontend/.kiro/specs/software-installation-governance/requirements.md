# Requirements Document

## Introduction

Phase 3 of the Gadget Management System introduces Software Installation Governance — a two-tier approval workflow that allows employees to request software installation on their assigned assets, IT Admins to review and triage those requests by risk level, and Management to make final decisions on escalated high-risk requests. The feature integrates into the existing React frontend, reusing established patterns for routing, data fetching, forms, tables, and role-based access control.

## Glossary

*   **Software\_Request**: A record representing an employee's request to install a specific software package on an assigned asset.
*   **Submit\_Form**: The modal dialog form used by an employee to submit a new Software\_Request.
*   **IT\_Admin\_Review\_Form**: The modal dialog form used by an IT Admin to review a PENDING\_REVIEW Software\_Request.
*   **Management\_Review\_Form**: The modal dialog form used by a Management user to review an ESCALATED\_TO\_MANAGEMENT Software\_Request.
*   **Software\_Requests\_Tab**: The tab or section on the Asset Detail page that lists Software\_Requests for that asset.
*   **Escalated\_Dashboard**: The dedicated page accessible to Management users that lists all ESCALATED\_TO\_MANAGEMENT Software\_Requests across all assets.
*   **Software\_Request\_Detail**: The detail view for a single Software\_Request, accessible from the Software\_Requests\_Tab or the Escalated\_Dashboard.
*   **data\_access\_impact**: The employee's self-assessed data access impact level (LOW, MEDIUM, or HIGH) submitted with the Software\_Request.
*   **risk\_level**: The IT Admin's verified technical risk assessment (LOW, MEDIUM, or HIGH) assigned during review. Drives escalation logic.
*   **SoftwareStatus**: The lifecycle status of a Software\_Request — one of PENDING\_REVIEW, ESCALATED\_TO\_MANAGEMENT, SOFTWARE\_INSTALL\_APPROVED, or SOFTWARE\_INSTALL\_REJECTED.
*   **ApiError**: The error class thrown by the API client when the backend returns a non-2xx response, carrying `status` (HTTP code) and `message` (from the response body).
*   **System**: The React frontend application.

---

## Requirements

### Requirement 1: Submit Software Installation Request

**User Story:** As an employee, I want to submit a software installation request for my assigned asset, so that IT Admin can review and approve the software I need.

#### Acceptance Criteria

1.  WHILE the authenticated user's role is `employee` AND the asset status is `ASSIGNED` AND the asset's assigned user matches the current user, THE System SHALL render a "Request Software Installation" button on the Asset Detail page.
2.  WHEN the employee clicks the "Request Software Installation" button, THE System SHALL open the Submit\_Form in a modal dialog.
3.  THE Submit\_Form SHALL contain the following required fields: software\_name (text), version (text), vendor (text), justification (textarea), license\_type (text), license\_validity\_period (text), and data\_access\_impact (select: LOW, MEDIUM, HIGH).
4.  WHEN the employee submits the Submit\_Form with all fields valid, THE System SHALL call `POST /assets/{asset_id}/software-requests` with the form values as the request body.
5.  WHEN the submission succeeds, THE System SHALL display a success toast with the message "Software installation request submitted. IT Admin will review your request." and close the Submit\_Form dialog.
6.  WHEN the submission succeeds, THE System SHALL invalidate the Software\_Requests\_Tab query cache so the new request appears in the list.
7.  IF the API returns a 400 error, THEN THE System SHALL display the error `message` from the response as an inline form error inside the Submit\_Form dialog.
8.  IF the API returns a 403 error, THEN THE System SHALL display a toast error with the message from the API response.
9.  IF the API returns a 404 error, THEN THE System SHALL display a toast error with the message from the API response.
10.  IF the API returns a 409 error, THEN THE System SHALL display a toast error with the message from the API response.
11.  THE Submit\_Form SHALL disable the submit button while the mutation is pending to prevent duplicate submissions.

---

### Requirement 2: List Software Requests for an Asset

**User Story:** As an IT Admin or assigned employee, I want to see all software installation requests for a specific asset, so that I can track their status and take action.

#### Acceptance Criteria

1.  WHILE the authenticated user's role is `it-admin`, THE System SHALL render the Software\_Requests\_Tab on the Asset Detail page for any asset.
2.  WHILE the authenticated user's role is `employee` AND the asset's assigned user matches the current user, THE System SHALL render the Software\_Requests\_Tab on the Asset Detail page.
3.  WHEN the Software\_Requests\_Tab is rendered, THE System SHALL call `GET /assets/{asset_id}/software-requests` with `page`, `page_size`, and any active filter parameters.
4.  THE Software\_Requests\_Tab SHALL display a table with columns: Software Name, Version, Vendor, Status (colored badge), Risk Level (or "—" if not yet reviewed), Data Access Impact, Requested By, Created At, and Actions.
5.  THE System SHALL render the SoftwareStatus badge using the following color mapping: PENDING\_REVIEW → info, ESCALATED\_TO\_MANAGEMENT → warning, SOFTWARE\_INSTALL\_APPROVED → success, SOFTWARE\_INSTALL\_REJECTED → danger.
6.  THE System SHALL render the risk\_level badge using the following color mapping: LOW → success, MEDIUM → info, HIGH → danger.
7.  THE System SHALL render the data\_access\_impact badge using the following color mapping: LOW → success, MEDIUM → info, HIGH → danger.
8.  THE Software\_Requests\_Tab SHALL include a Filters dialog containing: Status (select), Risk Level (select), Software Name (text), Vendor (text), License Validity Period (text), and Data Access Impact (select) filter fields.
9.  WHEN the user applies filters, THE System SHALL sync all active filter values to URL search params and reset the page to 1.
10.  THE Software\_Requests\_Tab SHALL include pagination controls and support `page` and `page_size` URL search params.
11.  WHEN no software requests exist for the asset, THE System SHALL display the message "No software installation requests for this asset."
12.  IF the API returns a 403 error, THEN THE System SHALL display an inline error with the message from the API response.
13.  IF the API returns a 404 error, THEN THE System SHALL display an inline error with the message from the API response.
14.  THE actions column SHALL render an eye icon button that navigates to the Software\_Request\_Detail view for that row.

---

### Requirement 3: View Software Request Detail

**User Story:** As an IT Admin, Management user, or assigned employee, I want to view the full details of a software installation request, so that I can understand the request context and take appropriate action.

#### Acceptance Criteria

1.  WHILE the authenticated user's role is `it-admin` OR `management`, THE System SHALL allow navigation to the Software\_Request\_Detail view for any Software\_Request.
2.  WHILE the authenticated user's role is `employee` AND the asset's assigned user matches the current user, THE System SHALL allow navigation to the Software\_Request\_Detail view.
3.  WHEN the Software\_Request\_Detail view is rendered, THE System SHALL call `GET /assets/{asset_id}/software-requests/{timestamp}` and display the response data.
4.  THE Software\_Request\_Detail SHALL display the following sections: Request Info (software\_name, version, vendor, justification, license\_type, license\_validity\_period), Impact Assessment (data\_access\_impact labeled "Employee Assessment", risk\_level labeled "IT Admin Assessment" — showing "Pending" if null), Status (status badge, created\_at, requested\_by), IT Admin Review (reviewed\_by, reviewed\_at, rejection\_reason if present), Management Review (management\_reviewed\_by, management\_reviewed\_at, management\_rejection\_reason if present, management\_remarks if present), and Installation (installation\_timestamp labeled "Approved/Installed At" if present).
5.  THE System SHALL render the IT Admin Review section only when `reviewed_by` is populated.
6.  THE System SHALL render the Management Review section only when `management_reviewed_by` is populated.
7.  THE System SHALL render the Installation section only when `installation_timestamp` is populated.
8.  WHILE the authenticated user's role is `it-admin` AND the Software\_Request status is `PENDING_REVIEW`, THE System SHALL render a "Review Request" button on the Software\_Request\_Detail view.
9.  WHILE the authenticated user's role is `management` AND the Software\_Request status is `ESCALATED_TO_MANAGEMENT`, THE System SHALL render a "Review Escalated Request" button on the Software\_Request\_Detail view.
10.  IF the API returns a 403 error, THEN THE System SHALL display an inline error with the message from the API response.
11.  IF the API returns a 404 error, THEN THE System SHALL display an inline error with the message from the API response.

---

### Requirement 4: IT Admin Review of Software Request

**User Story:** As an IT Admin, I want to review a pending software installation request by assigning a risk level and making an approve, escalate, or reject decision, so that requests are triaged correctly based on technical risk.

#### Acceptance Criteria

1.  WHEN the IT Admin clicks the "Review Request" button on the Software\_Request\_Detail view, THE System SHALL open the IT\_Admin\_Review\_Form in a modal dialog.
2.  THE IT\_Admin\_Review\_Form SHALL contain: a Risk Level field (select: LOW, MEDIUM, HIGH, required), a Decision field (radio or select: APPROVE, ESCALATE, REJECT, required), and a Rejection Reason field (textarea, required only when decision is REJECT).
3.  WHEN the IT Admin selects risk\_level `LOW`, THE System SHALL enable only the APPROVE and REJECT decision options and disable ESCALATE.
4.  WHEN the IT Admin selects risk\_level `MEDIUM` or `HIGH`, THE System SHALL enable only the ESCALATE and REJECT decision options and disable APPROVE.
5.  WHEN the IT Admin submits the IT\_Admin\_Review\_Form with all required fields valid, THE System SHALL call `PUT /assets/{asset_id}/software-requests/{timestamp}/review` with the form values as the request body.
6.  WHEN the review submission succeeds with decision `APPROVE`, THE System SHALL display a success toast "Software installation approved." and close the dialog.
7.  WHEN the review submission succeeds with decision `ESCALATE`, THE System SHALL display a success toast "Request escalated to Management for review." and close the dialog.
8.  WHEN the review submission succeeds with decision `REJECT`, THE System SHALL display a success toast "Software installation request rejected." and close the dialog.
9.  WHEN the review submission succeeds, THE System SHALL invalidate the Software\_Request\_Detail query cache so the updated status is reflected.
10.  IF the API returns a 400 error, THEN THE System SHALL display the error `message` from the response as an inline form error inside the IT\_Admin\_Review\_Form dialog.
11.  IF the API returns a 404 error, THEN THE System SHALL display a toast error with the message from the API response.
12.  IF the API returns a 409 error, THEN THE System SHALL display a toast error with the message from the API response.
13.  THE IT\_Admin\_Review\_Form SHALL disable the submit button while the mutation is pending.

---

### Requirement 5: Management Review of Escalated Software Request

**User Story:** As a Management user, I want to review an escalated software installation request and approve or reject it, so that high-risk software decisions receive appropriate oversight.

#### Acceptance Criteria

1.  WHEN the Management user clicks the "Review Escalated Request" button on the Software\_Request\_Detail view, THE System SHALL open the Management\_Review\_Form in a modal dialog.
2.  THE Management\_Review\_Form SHALL contain: a Decision field (radio or select: APPROVE, REJECT, required), a Remarks field (textarea, optional), and a Rejection Reason field (textarea, required only when decision is REJECT).
3.  WHEN the Management user submits the Management\_Review\_Form with all required fields valid, THE System SHALL call `PUT /assets/{asset_id}/software-requests/{timestamp}/management-review` with the form values as the request body.
4.  WHEN the management review submission succeeds with decision `APPROVE`, THE System SHALL display a success toast "Software installation approved by Management." and close the dialog.
5.  WHEN the management review submission succeeds with decision `REJECT`, THE System SHALL display a success toast "Software installation request rejected by Management." and close the dialog.
6.  WHEN the management review submission succeeds, THE System SHALL invalidate the Software\_Request\_Detail query cache so the updated status is reflected.
7.  IF the API returns a 400 error, THEN THE System SHALL display the error `message` from the response as an inline form error inside the Management\_Review\_Form dialog.
8.  IF the API returns a 404 error, THEN THE System SHALL display a toast error with the message from the API response.
9.  IF the API returns a 409 error, THEN THE System SHALL display a toast error with the message from the API response.
10.  THE Management\_Review\_Form SHALL disable the submit button while the mutation is pending.

---

### Requirement 6: Escalated Requests Dashboard

**User Story:** As a Management user, I want a dedicated dashboard listing all escalated software requests across all assets, so that I can efficiently find and action requests awaiting my review.

#### Acceptance Criteria

1.  THE System SHALL provide a dedicated Escalated\_Dashboard page accessible to users with role `management` at the existing `/requests` route.
2.  THE System SHALL render the escalated software requests table as the content of the `/requests` page for the `management` role. No new navigation item is required — management already has "Requests" in their nav.
3.  WHEN the Escalated\_Dashboard is rendered, THE System SHALL call `GET /software-requests/escalated` with `page`, `page_size`, and any active `risk_level` filter parameter.
4.  THE Escalated\_Dashboard SHALL display a table with columns: Asset ID (link to asset detail), Software Name, Version, Vendor, Risk Level (colored badge), Data Access Impact, Requested By, Reviewed By, Created At, and Actions.
5.  THE Escalated\_Dashboard SHALL include a Filters dialog containing a Risk Level filter (select: LOW, MEDIUM, HIGH).
6.  WHEN the user applies the risk\_level filter, THE System SHALL sync the value to URL search params and reset the page to 1.
7.  THE Escalated\_Dashboard SHALL include pagination controls and support `page` and `page_size` URL search params.
8.  WHEN no escalated requests exist, THE System SHALL display the message "No escalated software requests pending review."
9.  THE actions column SHALL render an eye icon button that navigates to the Software\_Request\_Detail view for that row.
10.  WHEN a Management user navigates to the Software\_Request\_Detail from the Escalated\_Dashboard, THE System SHALL display the "Review Escalated Request" button if the request status is still `ESCALATED_TO_MANAGEMENT`.
11.  IF the API returns a 403 error, THEN THE System SHALL display an inline error with the message from the API response.

---

### Requirement 7: Role-Based Access Control

**User Story:** As a system administrator, I want all software governance UI to be strictly gated by user role, so that users can only perform actions they are authorized for.

#### Acceptance Criteria

1.  THE System SHALL restrict the Escalated\_Dashboard route to users with role `management` using a `beforeLoad` guard that redirects unauthorized users to `/unauthorized`.
2.  THE System SHALL restrict the Software\_Request\_Detail route to users with roles `it-admin`, `management`, or `employee` using a `beforeLoad` guard.
3.  THE System SHALL not render the "Request Software Installation" button for users with roles `it-admin`, `management`, or `finance`.
4.  THE System SHALL not render the Software\_Requests\_Tab for users with roles `management` or `finance`.
5.  THE System SHALL not render the "Review Request" button for users with roles other than `it-admin`.
6.  THE System SHALL not render the "Review Escalated Request" button for users with roles other than `management`.
7.  THE System SHALL not render the Escalated\_Dashboard navigation item for users with roles other than `management`.

---

### Requirement 8: Query Key and Cache Management

**User Story:** As a developer, I want all software request queries to use the centralized query key factory, so that cache invalidation is consistent and type-safe across the feature.

#### Acceptance Criteria

1.  THE System SHALL define software request query keys in `src/lib/query-keys.ts` under a `softwareRequests` namespace, covering: list (per asset, with filter params), detail (per asset and timestamp), and escalated list (with filter params).
2.  WHEN a Software\_Request is submitted, reviewed, or management-reviewed, THE System SHALL invalidate the relevant query keys using the factory definitions — never raw string arrays.
3.  THE System SHALL encapsulate all `useQuery` and `useMutation` calls for software requests in custom hooks in `src/hooks/use-software-requests.ts`.
4.  THE System SHALL configure a non-zero `staleTime` on all software request list and detail queries.