# List Endpoints — By Role

All list endpoints use offset-based pagination (`page`, `page_size`) and return `PaginatedResponse`.

---

## IT Admin Endpoints

| # | Endpoint | Route | Lambda | Filters | Description |
|---|----------|-------|--------|---------|-------------|
| 1 | List Assets | `GET /assets` | ListAssets | `status`, `category`, `brand`, `model_name`, `date_from`, `date_to`, `sort_order` | All assets via EntityTypeIndex. Also serves employees (own assets only via EmployeeAssetIndex) |
| 2 | List Users | `GET /users` | ListUsers | `role`, `status`, `name`, `sort_order` | All users (EntityType=USER) |
| 3 | List All Issues | `GET /issues` | ListAllIssues | `status`, `category`, `sort_order` | All issues across all assets. IssueStatusIndex or IssueEntityIndex |
| 4 | List Pending Returns | `GET /assets/pending-returns` | ListPendingReturns | `sort_order` | Issues with status `REPLACEMENT_APPROVED`, filtered to assets with status `ISSUE_REPORTED` |
| 5 | List Returns (per asset) | `GET /assets/{asset_id}/returns` | ListReturns | `status`, `return_trigger`, `condition_assessment`, `sort_order` | Return records for a specific asset |
| 6 | List All Returns | `GET /returns` | ListAllReturns | `status`, `return_trigger`, `condition_assessment`, `sort_order` | All return records via MaintenanceEntityIndex (MaintenanceRecordType=RETURN) |
| 7 | List Disposals | `GET /disposals` | ListDisposals | `status`, `disposal_reason`, `date_from`, `date_to`, `sort_order` | All disposals. DisposalStatusIndex or DisposalEntityIndex |
| 8 | List Employee Signatures | `GET /users/{id}/signatures` | ListEmployeeSignatures | `assignment_date_from`, `assignment_date_to`, `sort_order` | Handover signatures for a specific employee with presigned URLs |
| 9 | List Maintenance History | `GET /maintenance-history` | ListMaintenanceHistory | `record_type` (ISSUE, SOFTWARE_REQUEST, RETURN, DISPOSAL), `sort_order` | All maintenance records via MaintenanceEntityIndex |

## Management Endpoints

| # | Endpoint | Route | Lambda | Filters | Description |
|---|----------|-------|--------|---------|-------------|
| 1 | List Pending Replacements | `GET /issues/pending-replacements` | ListPendingReplacements | `sort_order` | Issues with status `REPLACEMENT_REQUIRED` via IssueStatusIndex |
| 2 | List Pending Disposals | `GET /disposals/pending` | ListPendingDisposals | `disposal_reason`, `sort_order` | Disposals with status `DISPOSAL_PENDING` via DisposalStatusIndex |

## Management OR IT Admin Endpoints

| # | Endpoint | Route | Lambda | Filters | Description |
|---|----------|-------|--------|---------|-------------|
| 1 | List Asset Categories | `GET /categories` | ListAssetCategories | pagination only | All asset categories via CategoryEntityIndex. Uses `require_roles(["management", "it-admin"])` |

## Employee Endpoints

| # | Endpoint | Route | Lambda | Filters | Description |
|---|----------|-------|--------|---------|-------------|
| 1 | List My Software Requests | `GET /assets/software-requests/my` | ListMySoftwareRequests | `status`, `sort_order` | Current employee's software requests (filtered by RequestedBy) |
| 2 | List My Issues | `GET /issues/my` | ListMyIssues | `status`, `sort_order` | Current employee's issues (filtered by ReportedBy) |
| 3 | List Pending Signatures | `GET /users/me/pending-signatures` | ListPendingSignatures | pagination only | Pending handover/return documents requiring employee's signature |

## Multi-Role Endpoints (role-based logic inside handler)

| # | Endpoint | Route | Lambda | Allowed Roles | Role-Specific Behavior | Filters |
|---|----------|-------|--------|---------------|------------------------|---------|
| 1 | List Assets | `GET /assets` | ListAssets | it-admin, management, employee | Admin/mgmt: all assets. Employee: own assets only (EmployeeAssetIndex) | `status`, `category`, `brand`, `model_name`, `date_from`, `date_to`, `sort_order` |
| 2 | List Software Requests (per asset) | `GET /assets/{asset_id}/software-requests` | ListSoftwareRequests | it-admin, employee | IT admin: all for asset. Employee: must be assigned to asset, sees own only | `status`, `risk_level`, `software_name`, `vendor`, `license_validity_period`, `data_access_impact`, `sort_order` |
| 3 | List All Software Requests | `GET /assets/software-requests` | ListAllSoftwareRequests | it-admin, management, employee | IT admin: all. Management: forced to `ESCALATED_TO_MANAGEMENT`. Employee: own only | `status`, `risk_level`, `software_name`, `vendor`, `sort_order` |
| 4 | List Issues (per asset) | `GET /assets/{asset_id}/issues` | ListIssues | it-admin, employee, management | Employee must be assigned to asset | `status`, `sort_order` |
---

## Summary — Total: 21 List Endpoints

| Role | Exclusive | Shared | Total Access |
|------|-----------|--------|--------------|
| IT Admin | 9 | 5 (multi-role) + 1 (categories) + 1 (notifications) | 16 |
| Management | 2 | 4 (multi-role) + 1 (categories) + 1 (notifications) | 8 |
| Employee | 3 | 4 (multi-role) + 1 (notifications) | 8 |

> Note: `ListMyAssets` and `ListEscalatedRequests` are referenced in specs but don't have dedicated Lambdas. Their functionality is handled by `ListAssets` (employee path) and `ListAllSoftwareRequests` (management forced to escalated status) respectively.
