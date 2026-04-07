# Design Document: Issue Management

## Overview

Issue Management (Phase 4) adds a full lifecycle workflow for reporting, triaging, repairing, and replacing defective assets. The feature introduces three new routes, a custom hook file, query key extensions, a status badge component, and a suite of action dialogs.

The workflow is:

```
Employee reports issue → ISSUE_REPORTED
  → IT Admin triages → TROUBLESHOOTING
    → Path A: Start Repair → UNDER_REPAIR
        → Send to Warranty → SEND_WARRANTY
        → Complete Repair → RESOLVED
    → Path B: Request Replacement → REPLACEMENT_REQUIRED (PENDING_APPROVAL in UI)
        → Management Approves → REPLACEMENT_APPROVED
        → Management Rejects → REPLACEMENT_REJECTED
```

Two distinct views exist:
- **IT Admin**: "Maintenance Hub" — card-based list with Requests / Ongoing Repairs / Maintenance History tabs
- **Employee**: "Requests" — table-based list with status-filter tabs and a Report Issue button

---

## Architecture

```mermaid
graph TD
  A[Employee - Asset Detail Page] -->|Report Issue button| B[SubmitIssueDialog]
  B -->|POST /assets/:id/issues| C[API]
  D[/maintenance route] -->|IT Admin view| E[MaintenanceHubPage]
  D -->|Employee view| F[RequestsPage]
  E --> G[IssueCard list + tabs]
  F --> H[IssueTable + tabs]
  G -->|View Details| I[/assets/:id/issues/:ts route]
  H -->|Eye icon| I
  I --> J[IssueDetailPage]
  J -->|role + status| K[Action Buttons]
  K --> L[StartRepairDialog]
  K --> M[SendWarrantyDialog]
  K --> N[CompleteRepairDialog]
  K --> O[RequestReplacementDialog]
  K --> P[ManagementReviewDialog]
  Q[/pending-replacements route] -->|Management only| R[PendingReplacementsPage]
  R -->|Eye icon| I
```

All data fetching is routed through `src/hooks/use-issues.ts`. Components never call `useQuery` or `useMutation` directly.

---

## Components and Interfaces

### New Route Files

| Route file | URL | Allowed roles |
|---|---|---|
| `_authenticated/requests.tsx` | `/maintenance` | `it-admin`, `employee` |
| `_authenticated/assets.$asset_id.issues.$timestamp.tsx` | `/assets/:asset_id/issues/:timestamp` | `it-admin`, `management`, `employee` (assignee only) |
| `_authenticated/pending-replacements.tsx` | `/pending-replacements` | `management` |

> Note: `maintenances.tsx` already exists as a stub. It will be replaced with the full implementation.

### New Component Files

```
src/components/issues/
  IssueStatusBadge.tsx          — colored badge for IssueStatus
  IssueCard.tsx                 — card used in IT Admin tab lists
  SubmitIssueDialog.tsx         — employee report issue modal
  UploadIssuePhotosDialog.tsx   — drag-drop photo upload (post-submit step)
  StartRepairDialog.tsx         — IT Admin: resolve-repair action
  SendWarrantyDialog.tsx        — IT Admin: send-warranty action
  CompleteRepairDialog.tsx      — IT Admin: complete-repair action
  RequestReplacementDialog.tsx  — IT Admin: request-replacement action
  ManagementReviewIssueDialog.tsx — Management: approve/reject replacement
```

### Hook: `src/hooks/use-issues.ts`

Exports:

```ts
// Queries
useIssues(assetId: string, filters: ListIssuesFilter, page: number, pageSize?: number)
useIssueDetail(assetId: string, timestamp: string)
usePendingReplacements(page: number, pageSize?: number)

// Mutations
useSubmitIssue(assetId: string)
useGenerateIssueUploadUrls(assetId: string, timestamp: string)
useTriageIssue(assetId: string, timestamp: string)          // internal — triage is implicit
useResolveRepair(assetId: string, timestamp: string)
useSendWarranty(assetId: string, timestamp: string)
useCompleteRepair(assetId: string, timestamp: string)
useRequestReplacement(assetId: string, timestamp: string)
useManagementReviewIssue(assetId: string, timestamp: string)
```

### Query Key Extensions (`src/lib/query-keys.ts`)

```ts
issues: {
  all: () => ['issues'] as const,
  list: (assetId: string, filters: ListIssuesFilter) =>
    [...queryKeys.issues.all(), 'list', assetId, filters] as const,
  detail: (assetId: string, timestamp: string) =>
    [...queryKeys.issues.all(), 'detail', assetId, timestamp] as const,
  pendingReplacements: (filters: ListPendingReplacementsFilter) =>
    [...queryKeys.issues.all(), 'pending-replacements', filters] as const,
}
```

---

## Data Models

All types are already defined in `src/lib/models/types.ts`. Key types used:

```ts
// Existing in types.ts — no additions needed
IssueStatus
IssueListItem
ListIssuesFilter
ListIssuesResponse
GetIssueResponse
SubmitIssueRequest / SubmitIssueResponse
ResolveRepairRequest / ResolveRepairResponse
SendWarrantyRequest / SendWarrantyResponse
CompleteRepairRequest / CompleteRepairResponse
RequestReplacementRequest / RequestReplacementResponse
ManagementReviewIssueRequest / ManagementReviewIssueResponse
PendingReplacementListItem
ListPendingReplacementsResponse
```

### Issue Status → Badge Mapping

```ts
// src/lib/models/labels.ts addition
export const ISSUE_STATUS_LABELS: Record<IssueStatus, string> = {
  ISSUE_REPORTED:        'Issue Reported',
  TROUBLESHOOTING:       'Troubleshooting',
  UNDER_REPAIR:          'Under Repair',
  SEND_WARRANTY:         'Sent to Warranty',
  RESOLVED:              'Resolved',
  PENDING_APPROVAL:      'Pending Approval',
  REPLACEMENT_APPROVED:  'Replacement Approved',
  REPLACEMENT_REJECTED:  'Replacement Rejected',
}
```

Badge variants per status:

| Status | Badge variant |
|---|---|
| `ISSUE_REPORTED` | `danger` |
| `TROUBLESHOOTING` | `warning` |
| `UNDER_REPAIR` | `info` |
| `SEND_WARRANTY` | `info` |
| `RESOLVED` | `success` |
| `PENDING_APPROVAL` | `warning` |
| `REPLACEMENT_APPROVED` | `success` |
| `REPLACEMENT_REJECTED` | `danger` |

### Action Button Visibility Matrix

| Role | Status | Buttons shown |
|---|---|---|
| `it-admin` | `TROUBLESHOOTING` | Start Repair, Request Replacement |
| `it-admin` | `UNDER_REPAIR` | Send to Warranty, Complete Repair |
| `it-admin` | `SEND_WARRANTY` | Complete Repair |
| `management` | `PENDING_APPROVAL` | Review Replacement Request |
| any | other | none |

### Tab → Status Filter Mapping

**IT Admin tabs:**

| Tab | Statuses fetched |
|---|---|
| Requests | `TROUBLESHOOTING` |
| Ongoing Repairs | `UNDER_REPAIR`, `SEND_WARRANTY`, `PENDING_APPROVAL`, `REPLACEMENT_APPROVED`, `REPLACEMENT_REJECTED` |
| Maintenance History | `RESOLVED` |

**Employee tabs:**

| Tab | Status filter |
|---|---|
| All Requests | (none) |
| Pending | `ISSUE_REPORTED` |
| In Review | `TROUBLESHOOTING`, `UNDER_REPAIR`, `SEND_WARRANTY` |
| Approved | `REPLACEMENT_APPROVED`, `RESOLVED` |
| Rejected | `REPLACEMENT_REJECTED` |

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Valid issue descriptions are submitted

*For any* non-empty, non-whitespace-only issue description string, submitting the form should call `POST /assets/{asset_id}/issues` with that description in the request body — the mutation should be invoked for all valid inputs, not just specific examples.

**Validates: Requirements 1.3**

### Property 2: Whitespace-only descriptions are rejected

*For any* string composed entirely of whitespace characters (including the empty string), attempting to submit it as an issue description should be rejected by form validation and the mutation should not be called.

**Validates: Requirements 1.3**

### Property 3: Submit button is disabled while pending

*For any* form submission in progress (`isPending = true`), the submit button should be disabled and a loading indicator should be visible — this holds regardless of which action dialog is open.

**Validates: Requirements 1.8, 7.6, 8.6, 9.6, 10.8, 11.9**

### Property 4: Non-image files are rejected by the upload zone

*For any* file whose MIME type is not `image/jpeg` or `image/png`, the drag-drop upload zone should reject it with an inline validation message and must not call the upload URL generation API.

**Validates: Requirements 2.7**

### Property 5: Tab filter mapping is correct

*For any* active tab value on the Maintenance Hub (Requests, Ongoing Repairs, Maintenance History), the issues query should be called with the exact set of status filters defined in the tab-to-status mapping — no extra statuses and no missing statuses.

**Validates: Requirements 3.5, 3.6, 3.7**

### Property 6: Issue card renders all required fields

*For any* `IssueListItem` object, the rendered `IssueCard` component should contain: a ticket ID derived from `asset_id` + truncated `timestamp`, the `issue_description`, the `asset_id`, a relative time string from `created_at`, the `reported_by` value, a status badge, and a "View Details" link.

**Validates: Requirements 3.8**

### Property 7: URL search params round-trip for tab and page

*For any* combination of active tab and page number on the Maintenance Hub, navigating to the URL with those search params should restore the same tab and page state — the state is fully recoverable from the URL.

**Validates: Requirements 3.12**

### Property 8: Employee table renders all required columns

*For any* `IssueListItem` array rendered in the employee table, every row should contain cells for: Gadget/Service (asset icon + asset_id), Status badge, Reported By, Date Submitted (via `formatDate`), and an Actions column with an eye icon linking to the Issue Detail page.

**Validates: Requirements 4.4**

### Property 9: Issue detail renders correct sections based on data

*For any* `GetIssueResponse` object, the Issue Detail page should: always render the Issue Info section with `issue_description` and `action_path`; render the Evidence Photos section (showing thumbnails or "No photos attached"); render the Triage section only when `triaged_by` is populated; render Repair Details only when `action_path = "REPAIR"`; render Replacement Details only when `action_path = "REPLACEMENT"`; render Management Review only when `management_reviewed_by` is populated.

**Validates: Requirements 5.3–5.9**

### Property 10: Action button visibility matches role-status matrix

*For any* combination of user role and issue status, the set of rendered action buttons on the Issue Detail page should exactly match the role-status matrix — no extra buttons and no missing buttons for any valid (role, status) pair.

**Validates: Requirements 6.1–6.5**

### Property 11: Required field validation blocks submission

*For any* form where a field is conditionally required — `replacement_justification` (always required in Request Replacement), `rejection_reason` (required when `decision = REJECT` in Management Review) — submitting with an empty or whitespace-only value for that field should be blocked by form validation and the mutation should not be called.

**Validates: Requirements 10.2, 11.10**

### Property 12: Pending replacements table renders all required columns

*For any* `PendingReplacementListItem` array, every row in the Pending Replacements table should contain cells for: Asset ID (linked to asset detail), Issue Description (truncated), Action Path, Replacement Justification (truncated), Reported By, Triaged By, Resolved By, Created At (via `formatDate`), and an Actions eye icon linking to Issue Detail.

**Validates: Requirements 12.3**

### Property 13: Issue status badge covers all statuses

*For any* `IssueStatus` value, the `IssueStatusBadge` component should render a non-empty label string and a valid badge variant (`danger`, `warning`, `info`, or `success`) — no status value should fall through to an undefined label or missing variant.

**Validates: Requirements 13.1–13.8**

### Property 14: Query key factory produces unique, stable keys

*For any* two distinct combinations of `(assetId, filters)` or `(assetId, timestamp)`, the `queryKeys.issues` factory should produce different key arrays; and for the same inputs, it should always produce structurally equal key arrays.

**Validates: Requirements 14.1**

### Property 15: Route guards redirect unauthorized roles

*For any* user role not in the allowed list for a given route (`/maintenance` allows `it-admin` and `employee`; `/pending-replacements` allows `management` only; `/assets/:id/issues/:ts` allows `it-admin`, `management`, and assignee `employee`), the `beforeLoad` guard should throw a redirect to `/unauthorized`.

**Validates: Requirements 3.1, 12.1, 15.1**

---

## Error Handling

Following the project's error feedback protocol:

| Error source | Handling |
|---|---|
| Mutation errors (action buttons, form submits) | `toast.error(err.message)` |
| 400 form validation errors | Inline `alert-danger` or `<FieldError>` inside the dialog |
| Query loading errors (`useQuery`) | Inline `<div className="alert-danger">` on the page |
| S3 PUT upload failures | `toast.error("One or more photo uploads failed. Please try again.")` |
| 403 / 409 on issue submit | `toast.error(err.message)` |

All mutations must have an `onError` handler. No mutation error should be silently swallowed.

Loading states: every submit button is disabled and shows a loading indicator while `isPending` is true (via `form.state.isSubmitting` or `mutation.isPending`).

---

## Testing Strategy

### Unit Tests

Focus on specific examples, edge cases, and pure logic:

- `IssueStatusBadge` renders correct label and variant for each `IssueStatus` value
- Action button visibility: one test per role-status combination in the matrix
- `replacement_justification` validation: empty string, whitespace-only string, valid string
- `rejection_reason` required-when-reject validation
- `ISSUE_STATUS_LABELS` covers all `IssueStatus` values (exhaustiveness check)
- `queryKeys.issues` factory produces stable, unique keys for different inputs

### Property-Based Tests

Using a property-based testing library (e.g. `fast-check` for TypeScript):

Each property test runs a minimum of 100 iterations.

**Property 1 — Issue submission grows the issue list**
```
// Feature: issue-management, Property 1: issue submission grows the issue list
// For any non-empty description string, submitting creates a new list entry
```

**Property 2 — Whitespace-only descriptions are rejected**
```
// Feature: issue-management, Property 2: whitespace-only descriptions are rejected
// Generate strings from /^\s+$/ and assert submission is blocked
```

**Property 3 — Issue status badge label coverage**
```
// Feature: issue-management, Property 3: issue status badge label coverage
// For any IssueStatus, IssueStatusBadge renders non-empty label and valid variant
```

**Property 4 — Action button visibility matches role-status matrix**
```
// Feature: issue-management, Property 4: action button visibility matches role-status matrix
// For any (role, status) pair, rendered buttons exactly match the matrix
```

**Property 5 — Replacement justification required for rejection**
```
// Feature: issue-management, Property 5: replacement justification required for rejection
// For any whitespace-only rejection_reason with decision=REJECT, form is invalid
```

**Property 8 — Non-image files are rejected**
```
// Feature: issue-management, Property 8: non-image files are rejected
// For any file with MIME type not in [image/jpeg, image/png], upload zone rejects it
```

Both unit and property tests are complementary. Unit tests catch concrete bugs in specific scenarios; property tests verify general correctness across the full input space.
