# WebSocket Real-Time Notifications: Frontend Implementation Prompt

## Context

You are migrating the notification system in the Gadget Management System (GMS) from polling to real-time WebSocket push. The backend is fully implemented — an API Gateway WebSocket API pushes notifications to connected clients the moment they are created. Your task is to integrate WebSocket connectivity into the existing frontend so users receive notifications instantly without polling.

The existing REST endpoints (`GET /notifications`, `PATCH /notifications/{notification_id}`) remain unchanged and are still used for notification history and mark-as-read. The WebSocket is purely an additive real-time delivery channel.

---

## Architecture Overview

```
DynamoDB Stream → NotificationProcessor Lambda
                    ├── Writes notification to DynamoDB (existing)
                    ├── Increments UnreadNotificationCount (existing)
                    └── Pushes to WebSocket (NEW)
                          ├── Queries connections table by UserID
                          └── Calls post_to_connection for each active connection

Frontend ←── WebSocket ←── API Gateway WebSocket API ←── NotificationProcessor
```

---

## WebSocket Connection Details

### Endpoint

```
wss://{WEBSOCKET_API_ID}.execute-api.{REGION}.amazonaws.com/{ENV}
```

This URL is available as an SSM parameter at `/{project}/{env}/websocket/endpoint` and should be exposed to the frontend via environment variable (e.g. `VITE_WS_ENDPOINT` or `NEXT_PUBLIC_WS_ENDPOINT`).

### Authentication

The WebSocket API does **not** use a Cognito authorizer on the `$connect` route. Instead, the `$connect` Lambda validates the Cognito ID token passed as a query parameter:

```
wss://xxx.execute-api.region.amazonaws.com/dev?token={cognito_id_token}
```

- The token is the same Cognito ID token used in `Authorization: Bearer` headers for REST calls.
- The backend decodes and validates the JWT (issuer, signature via JWKS).
- On success, the connection is stored in DynamoDB with the user's `sub` (UserID) and Cognito groups.
- On failure, the WebSocket connection is rejected with a 401.

### Connection Lifecycle

| Event | Backend Behavior |
|---|---|
| `$connect` | Validates token, stores `{ ConnectionID, UserID, Groups, ConnectedAt, TTL }` in connections table |
| `$disconnect` | Deletes connection record from connections table |
| `$default` | No-op (returns 200) — the server only pushes, clients don't send actions |
| Stale connection | If `post_to_connection` gets a `GoneException`, the connection record is auto-deleted |

Connections have a 24-hour TTL. If the user's token expires or the browser tab is closed, the connection is cleaned up automatically.

---

## WebSocket Message Format

The backend sends exactly one message type. Every message received on the WebSocket will have this shape:

```json
{
  "type": "notification",
  "data": {
    "notification_type": "NEW_ASSET_ASSIGNED",
    "title": "New Asset Assigned",
    "message": "Asset AST-202603-5 has been assigned to you.",
    "reference_id": "AST-202603-5",
    "reference_type": "ASSET"
  }
}
```

### TypeScript Types (already defined in `types.ts`)

```typescript
export type WebSocketNotificationPayload = {
    notification_type: NotificationType
    title: string
    message: string
    reference_id: string
    reference_type: ReferenceType
}

export type WebSocketMessage = {
    type: "notification"
    data: WebSocketNotificationPayload
}
```

### All Possible `notification_type` Values

These match the existing `NotificationType` enum — no new types were added:

| notification_type | Target Role | reference_type |
|---|---|---|
| `ASSET_PENDING_APPROVAL` | management | ASSET |
| `REPLACEMENT_APPROVAL_NEEDED` | management | ISSUE |
| `SOFTWARE_INSTALL_ESCALATION` | management | SOFTWARE |
| `DISPOSAL_APPROVAL_NEEDED` | management | ASSET |
| `ASSET_APPROVED` | it-admin | ASSET |
| `ASSET_REJECTED` | it-admin | ASSET |
| `NEW_ISSUE_REPORTED` | it-admin | ISSUE |
| `REPLACEMENT_APPROVED` | it-admin | ISSUE |
| `REPLACEMENT_REJECTED` | it-admin | ISSUE |
| `NEW_SOFTWARE_INSTALL_REQUEST` | it-admin | SOFTWARE |
| `HANDOVER_ACCEPTED` | it-admin | ASSET |
| `AUDIT_DISPUTE_RAISED` | it-admin | AUDIT |
| `AUDIT_NON_RESPONSE_ESCALATION` | it-admin | AUDIT |
| `NEW_ASSET_ASSIGNED` | employee (specific) | ASSET |
| `HANDOVER_FORM_READY` | employee (specific) | ASSET |
| `SOFTWARE_INSTALL_APPROVED` | employee (specific) | SOFTWARE |
| `SOFTWARE_INSTALL_REJECTED` | employee (specific) | SOFTWARE |
| `ISSUE_UNDER_REPAIR` | employee (specific) | ISSUE |
| `ISSUE_SENT_TO_WARRANTY` | employee (specific) | ISSUE |
| `ISSUE_RESOLVED` | employee (specific) | ISSUE |
| `RETURN_INITIATED` | employee (specific) | RETURN |
| `AUDIT_CONFIRMATION_REQUIRED` | employee (specific) | AUDIT |
| `AUDIT_FINAL_ACKNOWLEDGEMENT` | employee (specific) | AUDIT |
| `AUDIT_DISPUTE_REVIEWED` | employee (specific) | AUDIT |
| `AUDIT_REMINDER` | employee (specific) | AUDIT |
| `ASSET_DISPOSED_WRITEOFF` | finance | DISPOSAL |
| `REPLACEMENT_APPROVED_INFO` | finance | ISSUE |

---

## What to Implement

### 1. WebSocket Connection Manager (Hook / Service)

Create a reusable WebSocket connection manager that handles the full lifecycle. This should be a singleton or context-provided service — not per-component.

**Responsibilities:**
- Connect on login (after Cognito authentication succeeds and ID token is available)
- Disconnect on logout or token expiry
- Auto-reconnect with exponential backoff on unexpected disconnection
- Parse incoming messages as `WebSocketMessage`
- Expose a way for UI components to subscribe to incoming notifications (callback, event emitter, or reactive state)

**Reconnection strategy:**
- On `onclose` (not triggered by user logout): attempt reconnect
- Backoff: 1s → 2s → 4s → 8s → 16s → 30s (cap at 30s)
- Reset backoff timer on successful connection
- Stop reconnecting if the user has logged out or the token is no longer valid
- On reconnect, use a fresh ID token (tokens expire, so always get the current one from Cognito)

**Example pseudocode:**

```typescript
const ws = new WebSocket(`${WS_ENDPOINT}?token=${idToken}`)

ws.onopen = () => {
  console.log("WebSocket connected")
  resetBackoff()
}

ws.onmessage = (event) => {
  const message: WebSocketMessage = JSON.parse(event.data)
  if (message.type === "notification") {
    handleIncomingNotification(message.data)
  }
}

ws.onclose = (event) => {
  if (!userLoggedOut) {
    scheduleReconnect()
  }
}

ws.onerror = (error) => {
  console.error("WebSocket error", error)
}
```

### 2. Notification State Updates on WebSocket Message

When a `WebSocketMessage` arrives, the frontend should:

1. **Increment the unread count** in the notification bell/badge in the header/navbar. This is the same `unread_count` field returned by `GET /notifications` — just increment it locally by 1.

2. **Show a toast/snackbar** with the notification `title` and `message`. The toast should be clickable and navigate to the relevant page based on `reference_type` and `reference_id` (see navigation mapping below).

3. **Prepend to the notification list** if the notification dropdown/panel is currently open. The WebSocket payload does not include `notification_id`, `is_read`, or `created_at` — so either:
   - Refetch the first page of `GET /notifications` to get the full item, or
   - Construct a temporary item for display and reconcile on next fetch

4. **Play a notification sound** (optional, respect user preference if you have a setting for it).

### 3. Navigation Mapping

When the user clicks a notification toast or a notification list item, navigate based on `reference_type`:

| reference_type | Navigation Target |
|---|---|
| `ASSET` | `/assets/{reference_id}` |
| `ISSUE` | `/assets/{reference_id}` (issues are under the asset detail page) |
| `SOFTWARE` | `/assets/{reference_id}` (software requests are under the asset detail page) |
| `DISPOSAL` | `/assets/{reference_id}` (disposals are under the asset detail page) |
| `RETURN` | `/assets/{reference_id}` (returns are under the asset detail page) |
| `AUDIT` | `/my-audit` (for employees) or `/audits` (for it-admin/management) |

For `AUDIT` type, check the user's role to determine the correct destination.

### 4. Remove Polling

If the frontend currently polls `GET /notifications` on an interval to check for new notifications, remove that polling mechanism. The WebSocket replaces it entirely.

Keep the initial `GET /notifications` call on page load to populate the notification list and unread count — that stays. Just remove the recurring interval.

### 5. Connection Status Indicator (Optional but Recommended)

Show a subtle indicator of WebSocket connection status somewhere in the UI (e.g. a small dot on the notification bell):

| State | Indicator |
|---|---|
| Connected | Green dot or no indicator (default healthy state) |
| Reconnecting | Yellow/orange pulsing dot |
| Disconnected (gave up) | Red dot with tooltip "Real-time notifications unavailable" |

This helps users understand if they're receiving live updates or need to manually refresh.

---

## Existing REST Endpoints (Unchanged)

These endpoints are NOT changing. Continue using them as before:

### List My Notifications
- `GET /notifications?page=1&page_size=20&is_read=false&sort_order=desc`
- Response: `{ items: [NotificationItem], count, total_items, total_pages, current_page, unread_count }`
- Use on page load and when opening the notification panel

### Mark Notification Read
- `PATCH /notifications/{notification_id}`
- Response: `MarkNotificationReadResponse`
- Use when user clicks/views a notification
- After marking read, decrement the local unread count by 1

---

## Integration Points with Existing UI

### Notification Bell (Header/Navbar)
- **Before**: Showed `unread_count` from the last `GET /notifications` call (or polling)
- **After**: Initialize from `GET /notifications` on page load. Increment by 1 on each WebSocket message. Decrement by 1 on each mark-as-read.

### Notification Dropdown/Panel
- **Before**: Fetched on open, maybe polled
- **After**: Fetched on open (still call `GET /notifications`). If open when a WebSocket message arrives, either prepend the new notification or refetch the first page.

### Toast/Snackbar System
- **Before**: No real-time toasts for notifications
- **After**: Show a toast for every incoming WebSocket notification with title, message, and a click-to-navigate action

---

## Edge Cases to Handle

1. **Multiple tabs**: Each tab opens its own WebSocket connection. The backend stores multiple connections per user and pushes to all of them. Each tab will independently receive the notification. Make sure the unread count doesn't get out of sync — consider using `BroadcastChannel` or `localStorage` events to coordinate between tabs, or simply let each tab manage its own state and reconcile on focus.

2. **Token refresh**: Cognito ID tokens expire (typically 1 hour). When the token refreshes, the existing WebSocket connection remains valid (the token was only checked at `$connect` time). However, if the connection drops and needs to reconnect, use the fresh token.

3. **Offline → Online**: When the browser comes back online after being offline, the WebSocket will have disconnected. The reconnection logic should handle this. On reconnect, refetch `GET /notifications` to catch any notifications missed while offline.

4. **Rapid notifications**: Multiple notifications can arrive in quick succession (e.g. an IT admin creates an audit batch, triggering notifications to all employees). Batch toast display — don't show 50 toasts at once. Consider grouping or showing "You have X new notifications" if more than 3 arrive within a short window.

5. **User logs out**: Close the WebSocket connection explicitly on logout. Don't attempt reconnection after logout.

---

## Environment Variable

Add one new environment variable to the frontend configuration:

| Variable | Value | Example |
|---|---|---|
| `VITE_WS_ENDPOINT` (or framework equivalent) | WebSocket API endpoint URL | `wss://abc123.execute-api.us-east-1.amazonaws.com/dev` |

This value comes from the SSM parameter `/{project}/{env}/websocket/endpoint` and should be set during deployment or in the `.env` file.
