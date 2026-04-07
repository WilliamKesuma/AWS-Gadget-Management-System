# Page Stat Card Endpoints

Stat card endpoints for non-dashboard pages. Each returns a single response object with all stat fields for that page context.

---

## Assets Page — IT Admin

**`GET /pages/assets/stats`**

Visible only to IT Admin on the `/assets` page.

### Response

```json
{
  "total_assets": 284,
  "in_stock": 120,
  "assigned": 148,
  "in_maintenance": 16
}
```

### Field Definitions

| Field | Type | Explanation |
|---|---|---|
| `total_assets` | `number` | Count of all assets excluding `DISPOSED`, `ASSET_PENDING_APPROVAL`, and `ASSET_REJECTED`. Same definition as dashboard total assets — the active inventory. |
| `in_stock` | `number` | Count of assets with status = `IN_STOCK`. |
| `assigned` | `number` | Count of assets with status = `ASSIGNED`. |
| `in_maintenance` | `number` | Count of assets in maintenance statuses: `UNDER_REPAIR`, `ISSUE_REPORTED`, `REPAIR_REQUIRED`. |

---

## Requests Page — IT Admin & Management

**`GET /pages/requests/it-admin/stats`**

Visible to IT Admin and Management on the `/requests` page.

### Response

```json
{
  "completed_today": 14,
  "total_active_requests": 24,
  "pending_returns": 5
}
```

### Field Definitions

| Field | Type | Explanation |
|---|---|---|
| `completed_today` | `number` | Count of issues + software requests that reached a terminal state today (since midnight UTC). Terminal states: issues in `COMPLETED`, `REPLACEMENT_APPROVED`, `REPLACEMENT_REJECTED`; software in `SOFTWARE_INSTALL_APPROVED`, `SOFTWARE_INSTALL_REJECTED`. |
| `total_active_requests` | `number` | Count of all issues + software requests NOT in a terminal state. Active across the entire system. |
| `pending_returns` | `number` | Count of returns with `resolved_status` = `RETURN_PENDING` (initiated but not yet completed). |

---

## Requests Page — Employee

**`GET /pages/requests/employee/stats`**

Visible to Employee on the `/requests` page. Replaces the current client-side counting from paginated data (page_size=100) which is incorrect for larger datasets.

### Response

```json
{
  "active_requests": 6,
  "pending_approval": 2,
  "resolved_monthly": 3
}
```

### Field Definitions

| Field | Type | Explanation |
|---|---|---|
| `active_requests` | `number` | Count of this employee's issues + software requests NOT in a terminal state. Issues not in `COMPLETED`, `REPLACEMENT_APPROVED`, `REPLACEMENT_REJECTED`; software not in `SOFTWARE_INSTALL_APPROVED`, `SOFTWARE_INSTALL_REJECTED`. |
| `pending_approval` | `number` | Count of this employee's requests in initial pending statuses: issues in `TROUBLESHOOTING`, software requests in `PENDING_REVIEW`. Waiting for first action. |
| `resolved_monthly` | `number` | Count of this employee's requests that reached a resolved/approved terminal state in the current calendar month. Issues in `COMPLETED` or `REPLACEMENT_APPROVED`; software in `SOFTWARE_INSTALL_APPROVED`. |

---

## Status Reference

### Terminal States (Issues)

| Status | Category |
|---|---|
| `COMPLETED` | Completed (final state) |
| `REPLACEMENT_APPROVED` | Terminal — approved |
| `REPLACEMENT_REJECTED` | Terminal — rejected |

### Terminal States (Software)

| Status | Category |
|---|---|
| `SOFTWARE_INSTALL_APPROVED` | Terminal — approved |
| `SOFTWARE_INSTALL_REJECTED` | Terminal — rejected |

### Maintenance Statuses (Assets)

| Status | Category |
|---|---|
| `UNDER_REPAIR` | In maintenance |
| `ISSUE_REPORTED` | In maintenance |
| `REPAIR_REQUIRED` | In maintenance |
