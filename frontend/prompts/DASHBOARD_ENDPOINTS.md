# Dashboard Endpoints

Each role has a stats endpoint (single response with all stat card values) plus additional endpoints for list/chart data.

---

## Shared Endpoints (IT Admin & Management)

### Asset Distribution

**`GET /dashboard/asset-distribution`**

Top asset count per category, max 5 categories. Counts only active inventory (excludes `DISPOSED`, `ASSET_PENDING_APPROVAL`, `ASSET_REJECTED`).

#### Response

```json
{
  "items": [
    { "category": "Laptop", "count": 542 },
    { "category": "Mobile Phone", "count": 318 },
    { "category": "Tablet", "count": 124 },
    { "category": "Monitor", "count": 89 },
    { "category": "Others", "count": 211 }
  ]
}
```

#### Notes

- Sorted descending by count.
- Max 5 items. If more than 5 categories exist, the 5th item aggregates the rest as `"Others"`.

---

### Recent Activity

**`GET /dashboard/recent-activity`**

Latest activity across all users. Returns the most recent 5 entries.

#### Response

```json
{
  "items": [
    {
      "activity_id": "act-001",
      "activity": "Assigned asset to employee",
      "activity_type": "ASSIGNMENT",
      "actor_name": "Sarah Jenkins",
      "actor_role": "it-admin",
      "target_id": "AST-0042",
      "target_type": "ASSET",
      "timestamp": "2026-03-27T10:15:00Z"
    }
  ]
}
```

#### Field Definitions

| Field | Type | Explanation |
|---|---|---|
| `activity_id` | `string` | Unique identifier for the activity entry. |
| `activity` | `string` | Human-readable description of what happened (e.g. "Reported issue on asset", "Approved disposal request"). |
| `activity_type` | `string` | Category of the activity. One of: `ASSET_CREATION`, `ASSIGNMENT`, `RETURN`, `ISSUE`, `SOFTWARE_REQUEST`, `DISPOSAL`, `USER_CREATION`, `APPROVAL`, `HANDOVER`. |
| `actor_name` | `string` | Full name of the user who performed the action. |
| `actor_role` | `UserRole` | Role of the actor: `it-admin`, `management`, `employee`, `finance`. |
| `target_id` | `string` | ID of the target entity (asset_id, issue_id, user_id, disposal_id, etc.). |
| `target_type` | `string` | Type of the target entity. One of: `ASSET`, `ISSUE`, `SOFTWARE`, `DISPOSAL`, `USER`, `RETURN`. |
| `timestamp` | `string` | ISO 8601 timestamp of when the activity occurred. |

#### Notes

- Sorted descending by timestamp (newest first).
- Max 5 items returned.
- Used by both IT Admin and Management dashboards.

---

## IT Admin Dashboard

### Stats

**`GET /dashboard/it-admin/stats`**

#### Response

```json
{
  "total_assets": 284,
  "pending_issues": 42,
  "in_maintenance": 15
}
```

#### Field Definitions

| Field | Type | Explanation |
|---|---|---|
| `total_assets` | `number` | Count of all assets **excluding** `DISPOSED`, `ASSET_PENDING_APPROVAL`, and `ASSET_REJECTED`. Active inventory: `IN_STOCK`, `ASSIGNED`, `UNDER_REPAIR`, `RETURN_PENDING`, `DAMAGED`, `ISSUE_REPORTED`, `REPAIR_REQUIRED`, `DISPOSAL_REVIEW`, `DISPOSAL_PENDING`, `DISPOSAL_REJECTED`. |
| `pending_issues` | `number` | Count of issues in statuses actionable by IT Admin: `TROUBLESHOOTING`, `UNDER_REPAIR`, `SEND_WARRANTY`. Excludes terminal/management-owned statuses (`COMPLETED`, `REPLACEMENT_REQUIRED`, `REPLACEMENT_APPROVED`, `REPLACEMENT_REJECTED`). |
| `in_maintenance` | `number` | Count of assets currently in maintenance-related statuses: `UNDER_REPAIR`, `ISSUE_REPORTED`, `REPAIR_REQUIRED`. Assets not usable due to active issues. |

### Additional Data

- **Asset Distribution** → `GET /dashboard/asset-distribution` *(shared)*
- **Recent Activity** → `GET /dashboard/recent-activity` *(shared)*

---

## Management Dashboard

### Stats

**`GET /dashboard/management/stats`**

#### Response

```json
{
  "total_assets": 284,
  "pending_approvals": 24,
  "scheduled_disposals": 8
}
```

#### Field Definitions

| Field | Type | Explanation |
|---|---|---|
| `total_assets` | `number` | Same as IT Admin — count of all assets excluding `DISPOSED`, `ASSET_PENDING_APPROVAL`, and `ASSET_REJECTED`. |
| `pending_approvals` | `number` | Sum count of all items awaiting management action: **Asset Creation** (`ASSET_PENDING_APPROVAL`), **Replacement** (issues in `REPLACEMENT_REQUIRED`), **Software Escalation** (software requests in `ESCALATED_TO_MANAGEMENT`), **Disposal** (assets in `DISPOSAL_PENDING`). Only items actionable by management not yet in a terminal state. |
| `scheduled_disposals` | `number` | Count of disposals approved by management but not yet completed. Assets where disposal has been approved and admin still needs to enter disposal date and confirm data wipe — the intermediate state between management approval and final `DISPOSED`. |

### Approval Hub

**`GET /dashboard/management/approval-hub`**

Latest 3 items that need management approval. Pulls from the same pool as `pending_approvals` but returns the actual items.

#### Response

```json
{
  "items": [
    {
      "approval_type": "ASSET_CREATION",
      "target_id": "AST-0099",
      "title": "MacBook Pro 14\"",
      "subtitle": "M3, 32GB RAM",
      "requester_name": "Sarah Jenkins",
      "created_at": "2026-03-27T08:30:00Z"
    },
    {
      "approval_type": "REPLACEMENT",
      "target_id": "ISS-0042",
      "title": "Dell UltraSharp 27\"",
      "subtitle": "Defective panel",
      "requester_name": "Mark Thompson",
      "created_at": "2026-03-26T14:00:00Z"
    },
    {
      "approval_type": "DISPOSAL",
      "target_id": "DSP-0012",
      "title": "iPad Air (2019)",
      "subtitle": "End of lifecycle",
      "requester_name": "IT Admin",
      "created_at": "2026-03-25T09:00:00Z"
    }
  ]
}
```

#### Field Definitions

| Field | Type | Explanation |
|---|---|---|
| `approval_type` | `string` | One of: `ASSET_CREATION`, `REPLACEMENT`, `SOFTWARE_ESCALATION`, `DISPOSAL`. |
| `target_id` | `string` | ID of the item needing approval (asset_id, issue_id, software_request_id, or disposal_id). |
| `title` | `string` | Primary label — asset brand/model, software name, etc. |
| `subtitle` | `string` | Secondary detail — specs, reason, justification summary. |
| `requester_name` | `string` | Name of the person who initiated the request. |
| `created_at` | `string` | ISO 8601 timestamp of when the request was created. |

#### Notes

- Sorted descending by `created_at` (newest first).
- Max 3 items returned.

### Additional Data

- **Asset Distribution** → `GET /dashboard/asset-distribution` *(shared)*
- **Recent Activity** → `GET /dashboard/recent-activity` *(shared)*

---

## Employee Dashboard

### Stats

**`GET /dashboard/employee/stats`**

#### Response

```json
{
  "my_pending_requests": 2,
  "assigned_assets": 4,
  "pending_signatures": 1
}
```

#### Field Definitions

| Field | Type | Explanation |
|---|---|---|
| `my_pending_requests` | `number` | Count of the current employee's open requests not yet in a terminal state. **Issues** not in `COMPLETED`; **Software requests** not in `SOFTWARE_INSTALL_APPROVED` or `SOFTWARE_INSTALL_REJECTED`. Anything the employee submitted still in progress. |
| `assigned_assets` | `number` | Count of assets currently assigned to this employee — asset status = `ASSIGNED`. |
| `pending_signatures` | `number` | Count of documents awaiting this employee's digital signature. **Handover forms** needing acceptance; **Return forms** needing employee signature. |

---

## Finance Dashboard

### Stats

**`GET /dashboard/finance/stats`**

#### Response

```json
{
  "total_disposed": 148,
  "total_asset_value": 52430000,
  "pending_writeoffs": 24
}
```

#### Field Definitions

| Field | Type | Explanation |
|---|---|---|
| `total_disposed` | `number` | Count of all assets that have reached `DISPOSED` status — permanently locked, completed disposals. |
| `total_asset_value` | `number` | Sum of `cost` (original purchase cost) across all non-disposed assets. Active asset book value. **Monetary value, not a count.** |
| `pending_writeoffs` | `number` | Count of disposed assets where finance still needs to process the write-off. Disposal records with `finance_notification_status` = `QUEUED` or `COMPLETED` that finance has been notified about but hasn't actioned yet. |

---

## Status Reference

### Asset Statuses

| Status | Category |
|---|---|
| `ASSET_PENDING_APPROVAL` | Pre-inventory (excluded from total assets) |
| `ASSET_REJECTED` | Pre-inventory (excluded from total assets) |
| `IN_STOCK` | Active inventory |
| `ASSIGNED` | Active inventory |
| `UNDER_REPAIR` | Active inventory (maintenance) |
| `ISSUE_REPORTED` | Active inventory (maintenance) |
| `REPAIR_REQUIRED` | Active inventory (maintenance) |
| `DAMAGED` | Active inventory |
| `RETURN_PENDING` | Active inventory |
| `DISPOSAL_REVIEW` | Active inventory |
| `DISPOSAL_PENDING` | Active inventory (pending management approval) |
| `DISPOSAL_REJECTED` | Active inventory |
| `DISPOSED` | Terminal (excluded from total assets) |

### Issue Statuses

| Status | Terminal? |
|---|---|
| `TROUBLESHOOTING` | No — IT Admin actionable |
| `UNDER_REPAIR` | No — IT Admin actionable |
| `SEND_WARRANTY` | No — IT Admin actionable |
| `REPLACEMENT_REQUIRED` | No — Management actionable |
| `REPLACEMENT_APPROVED` | Yes |
| `REPLACEMENT_REJECTED` | Yes |
| `COMPLETED` | Yes (final state) |

### Software Statuses

| Status | Terminal? |
|---|---|
| `PENDING_REVIEW` | No — IT Admin actionable |
| `ESCALATED_TO_MANAGEMENT` | No — Management actionable |
| `SOFTWARE_INSTALL_APPROVED` | Yes |
| `SOFTWARE_INSTALL_REJECTED` | Yes |

### Activity Types

| Type | Description |
|---|---|
| `ASSET_CREATION` | New asset created/uploaded |
| `ASSIGNMENT` | Asset assigned to employee |
| `RETURN` | Return initiated or completed |
| `ISSUE` | Issue reported or status changed |
| `SOFTWARE_REQUEST` | Software install requested or reviewed |
| `DISPOSAL` | Disposal initiated, approved, or completed |
| `USER_CREATION` | New user account created |
| `APPROVAL` | Management approved/rejected a request |
| `HANDOVER` | Employee accepted handover |

### Target Types

| Type | Description |
|---|---|
| `ASSET` | Target is an asset (target_id = asset_id) |
| `ISSUE` | Target is an issue (target_id = issue_id) |
| `SOFTWARE` | Target is a software request (target_id = software_request_id) |
| `DISPOSAL` | Target is a disposal (target_id = disposal_id) |
| `USER` | Target is a user (target_id = user_id) |
| `RETURN` | Target is a return (target_id = return_id) |

### Approval Types

| Type | Source Status |
|---|---|
| `ASSET_CREATION` | Asset in `ASSET_PENDING_APPROVAL` |
| `REPLACEMENT` | Issue in `REPLACEMENT_REQUIRED` |
| `SOFTWARE_ESCALATION` | Software request in `ESCALATED_TO_MANAGEMENT` |
| `DISPOSAL` | Asset in `DISPOSAL_PENDING` |
