# Frontend Implementation Prompt — Notifications

## Context

You are building the React frontend for the Notifications feature of the Gadget Management System. The backend API is fully implemented. Notifications are visible to all authenticated users — every role receives notifications relevant to their responsibilities.

## API Endpoints

| Method | Path | Role(s) | Purpose |
|--------|------|---------|---------|
| GET | `/notifications` | Any authenticated user | List the caller's notifications (paginated, filterable by read status), includes `unread_count` |
| PATCH | `/notifications/{notification_id}` | Any authenticated user | Mark a single notification as read |

---

## TypeScript Types (already defined in `types.ts`)

```ts
// Notification Type enum
type NotificationType =
    | "ASSET_PENDING_APPROVAL"
    | "REPLACEMENT_APPROVAL_NEEDED"
    | "SOFTWARE_INSTALL_ESCALATION"
    | "DISPOSAL_APPROVAL_NEEDED"
    | "ASSET_APPROVED"
    | "ASSET_REJECTED"
    | "NEW_ISSUE_REPORTED"
    | "REPLACEMENT_APPROVED"
    | "REPLACEMENT_REJECTED"
    | "NEW_SOFTWARE_INSTALL_REQUEST"
    | "HANDOVER_ACCEPTED"
    | "AUDIT_DISPUTE_RAISED"
    | "AUDIT_NON_RESPONSE_ESCALATION"
    | "NEW_ASSET_ASSIGNED"
    | "HANDOVER_FORM_READY"
    | "SOFTWARE_INSTALL_APPROVED"
    | "SOFTWARE_INSTALL_REJECTED"
    | "ISSUE_UNDER_REPAIR"
    | "ISSUE_SENT_TO_WARRANTY"
    | "ISSUE_RESOLVED"
    | "RETURN_INITIATED"
    | "AUDIT_CONFIRMATION_REQUIRED"
    | "AUDIT_FINAL_ACKNOWLEDGEMENT"
    | "AUDIT_DISPUTE_REVIEWED"
    | "AUDIT_REMINDER"
    | "ASSET_DISPOSED_WRITEOFF"
    | "REPLACEMENT_APPROVED_INFO"

// Reference Type enum
type ReferenceType = "ASSET" | "ISSUE" | "SOFTWARE" | "DISPOSAL" | "AUDIT" | "RETURN"

// Single notification item
type NotificationItem = {
    notification_id: string
    notification_type: NotificationType
    title: string
    message: string
    reference_id: string
    reference_type: ReferenceType
    is_read: boolean
    created_at: string
}

// List notifications filter
type ListNotificationsFilter = PaginatedAPIFilter & {
    is_read?: boolean
}

// List notifications response (extends standard pagination with unread_count)
type ListNotificationsResponse = PaginatedAPIResponse<NotificationItem> & {
    unread_count: number
}

// Mark notification read response
type MarkNotificationReadResponse = {
    notification_id: string
    notification_type: NotificationType
    title: string
    message: string
    reference_id: string
    reference_type: ReferenceType
    is_read: boolean
    created_at: string
}
```

All paginated list responses follow this shape:
```ts
{ items: T[]; count: number; total_items: number; total_pages: number; current_page: number }
```

The `ListNotificationsResponse` adds `unread_count: number` at the top level alongside the standard pagination fields.

---

## Notification Type Labels (add to `labels.ts`)

Add a `NotificationTypeLabels` map to `labels.ts` for human-readable display:

```ts
import type { NotificationType, ReferenceType } from "./types"

export const NotificationTypeLabels: Record<NotificationType, string> = {
    ASSET_PENDING_APPROVAL: "Asset Pending Approval",
    REPLACEMENT_APPROVAL_NEEDED: "Replacement Approval Needed",
    SOFTWARE_INSTALL_ESCALATION: "Software Install Escalation",
    DISPOSAL_APPROVAL_NEEDED: "Disposal Approval Needed",
    ASSET_APPROVED: "Asset Approved",
    ASSET_REJECTED: "Asset Rejected",
    NEW_ISSUE_REPORTED: "New Issue Reported",
    REPLACEMENT_APPROVED: "Replacement Approved",
    REPLACEMENT_REJECTED: "Replacement Rejected",
    NEW_SOFTWARE_INSTALL_REQUEST: "New Software Install Request",
    HANDOVER_ACCEPTED: "Handover Accepted",
    AUDIT_DISPUTE_RAISED: "Audit Dispute Raised",
    AUDIT_NON_RESPONSE_ESCALATION: "Audit Non-Response Escalation",
    NEW_ASSET_ASSIGNED: "New Asset Assigned",
    HANDOVER_FORM_READY: "Handover Form Ready",
    SOFTWARE_INSTALL_APPROVED: "Software Install Approved",
    SOFTWARE_INSTALL_REJECTED: "Software Install Rejected",
    ISSUE_UNDER_REPAIR: "Issue Under Repair",
    ISSUE_SENT_TO_WARRANTY: "Issue Sent to Warranty",
    ISSUE_RESOLVED: "Issue Resolved",
    RETURN_INITIATED: "Return Initiated",
    AUDIT_CONFIRMATION_REQUIRED: "Audit Confirmation Required",
    AUDIT_FINAL_ACKNOWLEDGEMENT: "Audit Final Acknowledgement",
    AUDIT_DISPUTE_REVIEWED: "Audit Dispute Reviewed",
    AUDIT_REMINDER: "Audit Reminder",
    ASSET_DISPOSED_WRITEOFF: "Asset Disposed (Write-Off)",
    REPLACEMENT_APPROVED_INFO: "Replacement Approved (Info)",
}

export const ReferenceTypeLabels: Record<ReferenceType, string> = {
    ASSET: "Asset",
    ISSUE: "Issue",
    SOFTWARE: "Software",
    DISPOSAL: "Disposal",
    AUDIT: "Audit",
    RETURN: "Return",
}
```

---

## Features to Implement

### 1. Notification Bell Icon with Unread Badge (All Roles)

**Render condition:** Any authenticated user (all roles)

Add a notification bell icon to the application header/navbar. This is the primary entry point for notifications.

**Behavior:**

- On mount (and at a polling interval of 30 seconds), call `GET /notifications?page=1&page_size=1` to fetch the `unread_count` from the response. You only need the `unread_count` field — the items are not displayed here.
- If `unread_count > 0`, show a badge on the bell icon displaying the count. If `unread_count > 99`, display "99+".
- If `unread_count === 0`, hide the badge (show just the bell icon).
- Clicking the bell icon opens the Notifications Panel (Feature 2).

**Polling:**

- Poll `GET /notifications?page=1&page_size=1` every 30 seconds to keep the badge count fresh.
- Stop polling when the Notifications Panel is open (the panel fetches its own data).
- Resume polling when the panel is closed.
- Use a React hook (e.g. `useNotificationPolling`) to encapsulate the polling logic with `setInterval` and cleanup on unmount.

---

### 2. Notifications Panel / Dropdown (All Roles)

**Render condition:** Any authenticated user (all roles)

When the user clicks the notification bell, open a dropdown panel or slide-over panel anchored to the bell icon.

**Panel contents:**

- **Header:** "Notifications" title with the unread count displayed (e.g. "Notifications (3 unread)").
- **Filter tabs:** Two tabs — "All" and "Unread".
  - "All" tab: Calls `GET /notifications` without `is_read` filter.
  - "Unread" tab: Calls `GET /notifications?is_read=false`.
- **Notification list:** A scrollable list of `NotificationItem` entries.

**Each notification item displays:**

| Element | Source | Notes |
|---------|--------|-------|
| Title | `title` | Bold if `is_read === false` |
| Message | `message` | Truncate to 2 lines if long |
| Type badge | `notification_type` | Use `NotificationTypeLabels` for display. Color based on category (see badge colors below) |
| Time | `created_at` | Relative time format (e.g. "5 min ago", "2 hours ago", "3 days ago") |
| Read indicator | `is_read` | Show a blue dot or highlight for unread notifications |

**Interactions:**

- Clicking a notification item:
  1. Calls `PATCH /notifications/{notification_id}` to mark it as read (if not already read).
  2. Navigates to the relevant resource page based on `reference_type` and `reference_id` (see Feature 3).
  3. Closes the panel.
- "Mark as read" button (optional): A small icon button on each unread notification to mark it as read without navigating. Calls `PATCH /notifications/{notification_id}`.
- After marking a notification as read, update the local state to reflect `is_read = true` and decrement the `unread_count` in the header badge.

**Pagination:**

- Load the first page on panel open (`page=1`, `page_size=20`).
- Add a "Load more" button at the bottom of the list, or use infinite scroll, to fetch subsequent pages.
- Show "No notifications" if the list is empty.
- Show "No unread notifications" if the "Unread" tab is empty.

**Error handling:**

- If the API call fails, show a brief error message in the panel: "Failed to load notifications. Try again."
- If marking as read fails, show a toast: "Failed to mark notification as read."

---

### 3. Notification Click Navigation (All Roles)

**Render condition:** Any authenticated user (all roles)

When a user clicks a notification, navigate to the relevant resource page based on the `reference_type` and `reference_id` fields.

**Navigation mapping:**

| `reference_type` | Navigation Target | Route Example |
|-------------------|-------------------|---------------|
| `ASSET` | Asset Detail page | `/assets/{reference_id}` |
| `ISSUE` | Asset Issues tab | `/assets/{reference_id}/issues` |
| `SOFTWARE` | Asset Software Requests tab | `/assets/{reference_id}/software-requests` |
| `DISPOSAL` | Asset Disposal tab | `/assets/{reference_id}/disposal` |
| `AUDIT` | Asset Audit tab | `/assets/{reference_id}/audit` |
| `RETURN` | Asset Returns tab | `/assets/{reference_id}/returns` |

**Important notes on `reference_id` format:**

- For `ASSET` type notifications: `reference_id` is the asset ID (e.g. `"LAPTOP-2026-001"`). Navigate directly to `/assets/{reference_id}`.
- For `ISSUE`, `SOFTWARE`, `DISPOSAL`, `RETURN`, `AUDIT` type notifications: `reference_id` is the asset ID. Navigate to the asset's relevant sub-page (issues tab, software requests tab, etc.). The notification `message` field contains contextual detail about the specific record.
- For `HANDOVER_FORM_READY` and `HANDOVER_ACCEPTED` notifications: `reference_id` is the `HandoverID` (UUID v4). Navigate to `/assets/{asset_id}/handover/{reference_id}` — note that the asset ID is embedded in the notification `message` field if needed, but the frontend route should use the `reference_id` directly as the handover identifier.

If the target page doesn't exist or the user doesn't have permission, the target page's own error handling will display the appropriate message. No special handling needed in the notification click logic.

---

### 4. Notification Preferences (Optional Enhancement)

This is an optional future enhancement — do NOT implement this now. Mentioned for awareness only.

In the future, users may want to configure which notification types they receive or how they are alerted (e.g. mute certain types, set quiet hours). The current implementation delivers all notifications based on role — no user-level preferences.

---

## Conditional Rendering Summary

| Component / Action | it-admin | management | employee | finance |
|---|---|---|---|---|
| Notification bell icon in header | ✅ | ✅ | ✅ | ✅ |
| Unread badge on bell | ✅ | ✅ | ✅ | ✅ |
| Notifications panel/dropdown | ✅ | ✅ | ✅ | ✅ |
| Click notification → navigate | ✅ | ✅ | ✅ | ✅ |
| Mark notification as read | ✅ | ✅ | ✅ | ✅ |

All notification features are available to every authenticated role. The backend handles role-based targeting — each user only sees notifications addressed to them.

---

## Notification Type Categories and Badge Colors

Group notification types by category for consistent color coding:

| Category | Color | Notification Types |
|----------|-------|--------------------|
| Action Required | warning (amber/orange) | `ASSET_PENDING_APPROVAL`, `REPLACEMENT_APPROVAL_NEEDED`, `SOFTWARE_INSTALL_ESCALATION`, `DISPOSAL_APPROVAL_NEEDED`, `AUDIT_CONFIRMATION_REQUIRED`, `AUDIT_REMINDER` |
| Approved / Success | success (green) | `ASSET_APPROVED`, `REPLACEMENT_APPROVED`, `SOFTWARE_INSTALL_APPROVED`, `ISSUE_RESOLVED`, `HANDOVER_ACCEPTED` |
| Rejected / Negative | danger (red) | `ASSET_REJECTED`, `REPLACEMENT_REJECTED`, `SOFTWARE_INSTALL_REJECTED` |
| Informational | info (blue) | `NEW_ISSUE_REPORTED`, `NEW_SOFTWARE_INSTALL_REQUEST`, `NEW_ASSET_ASSIGNED`, `HANDOVER_FORM_READY`, `ISSUE_UNDER_REPAIR`, `ISSUE_SENT_TO_WARRANTY`, `RETURN_INITIATED`, `ASSET_DISPOSED_WRITEOFF`, `REPLACEMENT_APPROVED_INFO`, `AUDIT_FINAL_ACKNOWLEDGEMENT`, `AUDIT_DISPUTE_REVIEWED` |
| Escalation | warning (amber/orange) | `AUDIT_DISPUTE_RAISED`, `AUDIT_NON_RESPONSE_ESCALATION` |

Use these colors for the small type badge shown on each notification item in the panel.

---

## Read/Unread Visual Styling

| State | Styling |
|-------|---------|
| Unread (`is_read === false`) | Bold title, light background highlight (e.g. `bg-blue-50`), blue dot indicator on the left |
| Read (`is_read === true`) | Normal weight title, no background highlight, no dot indicator |

---

## Error Response Format

The API returns errors in the shape: `{ "message": "..." }`. Always display the `message` field to the user for 4xx errors.

---

## Notes

- There is no role restriction on the notification endpoints. Any authenticated user can call `GET /notifications` and `PATCH /notifications/{notification_id}`. The backend ensures users only see their own notifications (keyed by `PK = USER#<caller_user_id>`).
- The `unread_count` field is always present in the `GET /notifications` response, regardless of the `is_read` filter or pagination parameters. It always reflects the total unread count for the user.
- Notifications are automatically deleted after 90 days via DynamoDB TTL. No frontend action needed — old notifications simply stop appearing.
- The `notification_id` in the PATCH endpoint path is a UUID v4 string extracted from the notification's sort key. It is returned as `notification_id` in each `NotificationItem`.
- The `created_at` field is an ISO-8601 UTC timestamp. Convert to the user's local timezone for display and use relative time formatting (e.g. "5 min ago") for recent notifications, switching to absolute date format for older ones (e.g. "Mar 15, 2026").
- Polling interval of 30 seconds is a recommendation. You can make this configurable via an environment variable or constant. Avoid polling more frequently than every 15 seconds to minimize API load.
- The notification `title` and `message` fields are pre-generated by the backend. Display them as-is — no need to construct notification text on the frontend.
- All list endpoints support pagination with `page` and `page_size` query parameters. Default is page 1, 20 items per page.
- When the user is on the Notifications panel and marks a notification as read, optimistically update the UI (set `is_read = true` locally and decrement `unread_count`) before the PATCH response returns, then reconcile on response. If the PATCH fails, revert the optimistic update.
