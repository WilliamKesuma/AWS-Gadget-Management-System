# Backend List Endpoints Refactor — Prompt for Backend Developer

## Overview

We need to simplify and unify our list endpoints by:
1. Adding a `history` query parameter (boolean, defaults to `false`) to filter active vs. completed records
2. Making endpoints role-aware (backend filters by caller's role from Cognito token) instead of having separate `/my` endpoints
3. Adding an `asset_id` filter to global list endpoints for cross-filtering
4. Adding a management-specific "approvals" mode for endpoints that need management review

---

## 1. Status Lifecycle — Terminal (End-of-Life) States

These are derived from the requirements document. When `history=false` (default), exclude records in terminal states. When `history=true`, return ALL records including terminal ones.

### Issues (`IssueStatus`)
| Status | Active? | Terminal? | Notes |
|--------|---------|-----------|-------|
| `TROUBLESHOOTING` | ✅ | | IT Admin is investigating |
| `UNDER_REPAIR` | ✅ | | Repair in progress |
| `SEND_WARRANTY` | ✅ | | Sent for warranty repair |
| `REPLACEMENT_REQUIRED` | ✅ | | Awaiting management approval |
| `REPLACEMENT_APPROVED` | ✅ | | Approved, pending return process |
| `RESOLVED` | | ✅ | Repair completed successfully — END |
| `REPLACEMENT_REJECTED` | | ✅ | Management rejected replacement — END |

**Active filter (history=false):** `status NOT IN ('RESOLVED', 'REPLACEMENT_REJECTED')`

### Software Requests (`SoftwareStatus`)
| Status | Active? | Terminal? | Notes |
|--------|---------|-----------|-------|
| `PENDING_REVIEW` | ✅ | | Awaiting IT Admin review |
| `ESCALATED_TO_MANAGEMENT` | ✅ | | Escalated, awaiting management decision |
| `SOFTWARE_INSTALL_APPROVED` | | ✅ | Approved and installed — END |
| `SOFTWARE_INSTALL_REJECTED` | | ✅ | Rejected — END |

**Active filter (history=false):** `status NOT IN ('SOFTWARE_INSTALL_APPROVED', 'SOFTWARE_INSTALL_REJECTED')`

### Returns (`ReturnStatus` / `resolved_status`)
| Status | Active? | Terminal? | Notes |
|--------|---------|-----------|-------|
| `RETURN_PENDING` | ✅ | | Return initiated, awaiting completion |
| `COMPLETED` | | ✅ | Return fully completed — END |

**Active filter (history=false):** `resolved_status != 'COMPLETED'` (or `resolved_status IS NULL`)

### Disposals (`DisposalStatus` — mapped from `AssetStatus`)
| Status | Active? | Terminal? | Notes |
|--------|---------|-----------|-------|
| `DISPOSAL_PENDING` | ✅ | | Awaiting management approval |
| `DISPOSAL_ACCEPTED` | ✅ | | Approved, awaiting admin completion |
| `DISPOSED` | | ✅ | Disposal completed, record locked — END |
| `DISPOSAL_REJECTED` | | ✅ | Management rejected — END |

**Active filter (history=false):** `status NOT IN ('DISPOSED', 'DISPOSAL_REJECTED')`

### Statuses Requiring Management Approval (for Approvals page)
| Record Type | Status Requiring Management Action |
|-------------|-----------------------------------|
| Asset Creation | `ASSET_PENDING_APPROVAL` |
| Issue (Replacement) | `REPLACEMENT_REQUIRED` |
| Software Request | `ESCALATED_TO_MANAGEMENT` |
| Disposal | `DISPOSAL_PENDING` |

---

## 2. Endpoint Changes

### 2.1 Global List Issues — `GET /issues`

**Current:** IT Admin only (`ListAllIssues`). Separate `GET /issues/my` for employees.

**New behavior:**
- **Drop** `GET /issues/my` endpoint entirely
- `GET /issues` becomes multi-role:
  - `it-admin`: Returns ALL issues across all assets
  - `management`: Returns ALL issues across all assets (same as admin)
  - `employee`: Returns only issues where `reported_by_id` matches the caller's user ID (replaces `/issues/my`)
- **New query parameters:**
  - `history` (boolean, default `false`) — `false` = active only, `true` = all including terminal
  - `asset_id` (string, optional) — filter issues by a specific asset
- **Existing filters remain:** `status`, `category`, `sort_order`, `page`, `page_size`

**Backend logic:**
```python
# Pseudocode
role = get_caller_role()
user_id = get_caller_user_id()

if role == 'employee':
    # Filter by reported_by_id = user_id
    query = query.filter(reported_by_id=user_id)

if not history:
    TERMINAL_ISSUE_STATUSES = ['RESOLVED', 'REPLACEMENT_REJECTED']
    query = query.filter(status__not_in=TERMINAL_ISSUE_STATUSES)

if asset_id:
    query = query.filter(asset_id=asset_id)
```

### 2.2 Global List Software Requests — `GET /software-requests`

**Current:** `GET /assets/software-requests` (multi-role, management forced to ESCALATED). Separate `GET /assets/software-requests/my` for employees.

**New behavior:**
- **Change route** from `GET /assets/software-requests` to `GET /software-requests`
- **Drop** `GET /assets/software-requests/my` endpoint entirely
- Multi-role:
  - `it-admin`: Returns ALL software requests
  - `management`: Returns ALL software requests (no longer forced to ESCALATED_TO_MANAGEMENT — that filtering moves to the approvals page)
  - `employee`: Returns only requests where `requested_by_id` matches the caller's user ID
- **New query parameters:**
  - `history` (boolean, default `false`)
  - `asset_id` (string, optional)
- **Existing filters remain:** `status`, `risk_level`, `software_name`, `vendor`, `sort_order`, `page`, `page_size`

**Backend logic:**
```python
role = get_caller_role()
user_id = get_caller_user_id()

if role == 'employee':
    query = query.filter(requested_by_id=user_id)

if not history:
    TERMINAL_SOFTWARE_STATUSES = ['SOFTWARE_INSTALL_APPROVED', 'SOFTWARE_INSTALL_REJECTED']
    query = query.filter(status__not_in=TERMINAL_SOFTWARE_STATUSES)

if asset_id:
    query = query.filter(asset_id=asset_id)
```

### 2.3 Global List Returns — `GET /returns`

**Current:** `ListAllReturns` — IT Admin only.

**New behavior:**
- Multi-role:
  - `it-admin`: Returns ALL return records
  - `management`: Returns ALL return records
  - `employee`: **Not accessible** (return 403)
- **New query parameters:**
  - `history` (boolean, default `false`)
  - `asset_id` (string, optional)
- **Existing filters remain:** `status`, `return_trigger`, `condition_assessment`, `sort_order`, `page`, `page_size`

**Backend logic:**
```python
role = get_caller_role()

if role == 'employee':
    return 403  # Employees cannot list global returns

if not history:
    # Active = resolved_status is NULL or resolved_status != 'COMPLETED'
    query = query.filter(resolved_status__ne='COMPLETED')

if asset_id:
    query = query.filter(asset_id=asset_id)
```

### 2.4 Global List Disposals — `GET /disposals`

**Current:** `ListDisposals` — IT Admin only.

**New behavior:**
- Multi-role:
  - `it-admin`: Returns ALL disposal records
  - `management`: Returns ALL disposal records
  - `employee`: **Not accessible** (return 403)
- **New query parameters:**
  - `history` (boolean, default `false`)
  - `asset_id` (string, optional)
- **Existing filters remain:** `status`, `disposal_reason`, `date_from`, `date_to`, `sort_order`, `page`, `page_size`

**Backend logic:**
```python
role = get_caller_role()

if role == 'employee':
    return 403

if not history:
    TERMINAL_DISPOSAL_STATUSES = ['DISPOSED', 'DISPOSAL_REJECTED']
    query = query.filter(status__not_in=TERMINAL_DISPOSAL_STATUSES)

if asset_id:
    query = query.filter(asset_id=asset_id)
```

### 2.5 Per-Asset List Issues — `GET /assets/{asset_id}/issues`

**Current:** Multi-role. Employee must be assigned to asset.

**Changes:**
- Add `history` parameter (boolean, default `false`)
- Role behavior:
  - `it-admin` / `management`: See all issues for this asset
  - `employee`: Must be assigned to asset, sees only their own reported issues
- When `history=false`: exclude terminal statuses (`RESOLVED`, `REPLACEMENT_REJECTED`)
- When `history=true`: return all

### 2.6 Per-Asset List Software Requests — `GET /assets/{asset_id}/software-requests`

**Current:** Multi-role. Employee must be assigned to asset, sees own only.

**Changes:**
- Add `history` parameter (boolean, default `false`)
- Role behavior unchanged
- When `history=false`: exclude terminal statuses (`SOFTWARE_INSTALL_APPROVED`, `SOFTWARE_INSTALL_REJECTED`)
- When `history=true`: return all

### 2.7 Per-Asset List Returns — `GET /assets/{asset_id}/returns`

**Current:** IT Admin only via `ListReturns`.

**Changes:**
- Make multi-role: `it-admin`, `management` can access. `employee` returns 403.
- Add `history` parameter (boolean, default `false`)
- When `history=false`: exclude `COMPLETED` returns
- When `history=true`: return all

### 2.8 Per-Asset List Disposals — `GET /assets/{asset_id}/disposals`

**Current:** Not explicitly listed (may not exist yet).

**Changes:**
- Create if not exists
- Multi-role: `it-admin`, `management` can access. `employee` returns 403.
- Add `history` parameter (boolean, default `false`)
- Filters: `status`, `sort_order`, `page`, `page_size`
- When `history=false`: exclude `DISPOSED`, `DISPOSAL_REJECTED`
- When `history=true`: return all

---

## 3. Approvals Page Endpoints (Management)

The approvals page shows only records that need management's decision. These are existing endpoints that should remain but with clarified behavior:

### 3.1 Pending Asset Approvals — `GET /assets?status=ASSET_PENDING_APPROVAL`
- Already works via `ListAssets` with status filter. No change needed.
- For history mode: `GET /assets?status=ASSET_REJECTED` shows rejected ones, `GET /assets?status=IN_STOCK&remarks=...` shows approved ones. **OR** add a new dedicated endpoint (see 3.5).

### 3.2 Pending Replacements — `GET /issues/pending-replacements`
- **Keep as-is** for active pending items (status = `REPLACEMENT_REQUIRED`)
- **Add** `history` parameter:
  - `history=false` (default): Only `REPLACEMENT_REQUIRED` (needs action)
  - `history=true`: Include `REPLACEMENT_APPROVED` and `REPLACEMENT_REJECTED` (past decisions)
- Add `management_reviewed_by` to response items when `history=true` so UI can show who took action

### 3.3 Pending Disposals — `GET /disposals/pending`
- **Keep as-is** for active pending items (status = `DISPOSAL_PENDING`)
- **Add** `history` parameter:
  - `history=false` (default): Only `DISPOSAL_PENDING` (needs action)
  - `history=true`: Include `DISPOSED` and `DISPOSAL_REJECTED` (past decisions)
- Add `management_reviewed_by`, `management_reviewed_at` to response items when `history=true`

### 3.4 Pending Software Escalations — `GET /software-requests?status=ESCALATED_TO_MANAGEMENT`
- Already works via the global software requests endpoint with status filter
- For history: `GET /software-requests?history=true` with management-reviewed statuses
- **OR** create a dedicated endpoint (see 3.5)

### 3.5 (Optional) Unified Management Approvals — `GET /approvals`
If you prefer a single endpoint for the approvals page:

```
GET /approvals?history=false  (default — pending items only)
GET /approvals?history=true   (past decisions)
```

**Response:** Unified list with a `type` discriminator field:
```json
{
  "items": [
    {
      "type": "ASSET_CREATION",
      "asset_id": "...",
      "description": "...",
      "requested_by": "...",
      "created_at": "...",
      "status": "ASSET_PENDING_APPROVAL"
    },
    {
      "type": "REPLACEMENT",
      "asset_id": "...",
      "issue_id": "...",
      "description": "...",
      "reported_by": "...",
      "created_at": "...",
      "status": "REPLACEMENT_REQUIRED"
    }
  ]
}
```

This is optional — the frontend can also aggregate from individual endpoints.

---

## 4. Endpoints to DROP

| Endpoint | Reason |
|----------|--------|
| `GET /issues/my` (`ListMyIssues`) | Replaced by `GET /issues` with role-based filtering |
| `GET /assets/software-requests/my` (`ListMySoftwareRequests`) | Replaced by `GET /software-requests` with role-based filtering |
| `GET /maintenance-history` (`ListMaintenanceHistory`) | Replaced by the "All Requests" tab aggregating from individual endpoints with `history=true` on the frontend, OR keep if you want a single unified endpoint |

---

## 5. Endpoints to KEEP (unchanged)

| Endpoint | Notes |
|----------|-------|
| `GET /assets` | No changes — already multi-role |
| `GET /users` | No changes |
| `GET /categories` | No changes |
| `GET /users/{id}/signatures` | No changes |
| `GET /users/me/pending-signatures` | No changes |
| `GET /assets/pending-returns` | No changes — IT Admin only, shows assets needing return initiation |

---

## 6. Summary of New `history` Parameter Behavior

All list endpoints that support `history`:

| Parameter | Type | Default | Behavior |
|-----------|------|---------|----------|
| `history` | boolean | `false` | `false` = exclude terminal/end-of-lifecycle statuses (active only). `true` = return all records including completed/rejected ones |

The `history` parameter is additive to existing `status` filters:
- If `history=false` AND `status` is provided: apply both (intersection)
- If `history=false` AND no `status`: exclude terminal statuses
- If `history=true` AND `status` is provided: filter by that status only (no terminal exclusion)
- If `history=true` AND no `status`: return everything

---

## 7. Summary of New `asset_id` Filter

Global list endpoints (`GET /issues`, `GET /software-requests`, `GET /returns`, `GET /disposals`) should accept an optional `asset_id` query parameter to filter results to a specific asset. This enables the frontend to show filtered views when a user selects an asset from an autocomplete.

---

## 8. Response Schema Changes

### All list item responses should include `management_reviewed_by` and `management_reviewed_at` fields where applicable:
- Issue list items: already have these fields ✅
- Software request list items: already have these fields ✅  
- Disposal list items: already have these fields ✅
- Return list items: **Add** `management_reviewed_by` and `management_reviewed_at` if returns go through management review (currently they don't based on the requirements doc, so no change needed)

### No new response types needed — existing types are sufficient.

---

## 9. Migration Checklist

1. [ ] Add `history` query parameter parsing to all affected Lambda handlers
2. [ ] Add `asset_id` query parameter parsing to global list handlers
3. [ ] Modify `GET /issues` to be multi-role (add employee path filtering by `reported_by_id`)
4. [ ] Create `GET /software-requests` (new route) or modify `GET /assets/software-requests` to be the canonical route
5. [ ] Modify `GET /returns` to be multi-role (it-admin + management)
6. [ ] Modify `GET /disposals` to be multi-role (it-admin + management)
7. [ ] Add `history` support to per-asset endpoints (`/assets/{id}/issues`, `/assets/{id}/software-requests`, `/assets/{id}/returns`)
8. [ ] Create `GET /assets/{asset_id}/disposals` if it doesn't exist
9. [ ] Add `history` support to management approval endpoints (`/issues/pending-replacements`, `/disposals/pending`)
10. [ ] Deprecate/remove `GET /issues/my` and `GET /assets/software-requests/my`
11. [ ] Update API Gateway routes and Lambda permissions accordingly
12. [ ] Update CORS and authorizer configurations for any new routes
