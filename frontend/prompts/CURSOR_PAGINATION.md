# Cursor-Based Pagination: Frontend Migration Prompt

## Context

The backend has migrated all list endpoints from offset-based pagination (`page`/`page_size` with `total_items`/`total_pages`) to cursor-based pagination using DynamoDB's native `LastEvaluatedKey`. This gives O(1) per-page performance regardless of dataset size.

Your task is to update all frontend list views to use the new pagination contract.

---

## What Changed

### Request Parameters

**Before:**
```
GET /assets?page=2&page_size=20&status=ASSIGNED
```

**After:**
```
GET /assets?page_size=20&cursor=eyJQSyI6ICJBU1NFV...&status=ASSIGNED
```

| Parameter | Before | After |
|---|---|---|
| `page` | Required (integer, 1-based) | Removed |
| `page_size` | Optional (default 20, max 100) | Unchanged |
| `cursor` | Did not exist | Optional opaque string from previous response. Omit for first page. |

### Response Shape

**Before:**
```json
{
  "items": [...],
  "count": 20,
  "total_items": 145,
  "total_pages": 8,
  "current_page": 2
}
```

**After:**
```json
{
  "items": [...],
  "count": 20,
  "next_cursor": "eyJQSyI6ICJBU1NFV...",
  "has_next_page": true
}
```

| Field | Before | After |
|---|---|---|
| `items` | Array | Unchanged |
| `count` | Number | Unchanged |
| `total_items` | Number | Removed |
| `total_pages` | Number | Removed |
| `current_page` | Number | Removed |
| `next_cursor` | Did not exist | Opaque string or `null` |
| `has_next_page` | Did not exist | Boolean |

### Notifications Response (special case)

`GET /notifications` still returns `unread_count` alongside the paginated fields:
```json
{
  "items": [...],
  "count": 20,
  "next_cursor": "...",
  "has_next_page": true,
  "unread_count": 5
}
```

### Non-Paginated Endpoints (no changes)

- `GET /audits/{id}/versions` — returns a plain array, no pagination
- All single-item GET endpoints (`GET /assets/{id}`, etc.)
- All POST/PUT/PATCH mutation endpoints

---

## Updated TypeScript Types

```typescript
export type PaginatedAPIFilter = {
    page_size?: number
    cursor?: string
}

export type PaginatedAPIResponse<T> = {
    items: T[]
    count: number
    next_cursor: string | null
    has_next_page: boolean
}
```

---

## Affected Endpoints

Every list endpoint now uses cursor-based pagination:

| Endpoint | Notes |
|---|---|
| `GET /assets` | Status filter now uses optimized GSI query |
| `GET /users` | |
| `GET /assets/{id}/issues` | |
| `GET /assets/{id}/software-requests` | |
| `GET /assets/{id}/returns` | |
| `GET /assets/{id}/disposals` | |
| `GET /issues` | |
| `GET /software-requests` | |
| `GET /returns` | |
| `GET /disposals` | |
| `GET /disposals/pending` | |
| `GET /replacements/pending` | |
| `GET /categories` | |
| `GET /notifications` | Also returns `unread_count` |
| `GET /users/{id}/signatures` | |
| `GET /my/pending-signatures` | |
| `GET /audits` | |
| `GET /audits/{id}/snapshots` | |
| `GET /audits/{id}/non-responses` | |
| `GET /escalated-requests` | If exists |

---

## Pagination UI Pattern

Replace all numbered page navigation with Prev/Next buttons and an optional "Rows per page" selector.

### Component Behavior

```
[Rows per page: 20 ▾]    [← Previous]  [Next →]
```

- **First page**: `cursor` is omitted (or `undefined`). "Previous" button is disabled.
- **Next page**: Pass `next_cursor` from the current response as the `cursor` query param. 
- **Previous page**: Maintain a stack of previous cursors in component state. Pop the last cursor to go back.
- **Last page**: When `has_next_page` is `false` (or `next_cursor` is `null`), disable the "Next" button.
- **Rows per page change**: Reset to first page (clear cursor and cursor stack).
- **Filter/sort change**: Reset to first page (clear cursor and cursor stack).

### Cursor Stack for "Previous" Navigation

Since cursors are forward-only, maintain a local stack:

```typescript
const [cursorStack, setCursorStack] = useState<string[]>([])
const [currentCursor, setCurrentCursor] = useState<string | undefined>(undefined)

function goToNextPage(nextCursor: string) {
    setCursorStack(prev => [...prev, currentCursor ?? ''])
    setCurrentCursor(nextCursor)
}

function goToPreviousPage() {
    setCursorStack(prev => {
        const newStack = [...prev]
        const previousCursor = newStack.pop()
        setCurrentCursor(previousCursor || undefined)
        return newStack
    })
}

function resetPagination() {
    setCursorStack([])
    setCurrentCursor(undefined)
}

const canGoPrevious = cursorStack.length > 0
const canGoNext = response?.has_next_page ?? false
```

### API Call Pattern

```typescript
const params = new URLSearchParams()
params.set('page_size', pageSize.toString())
if (currentCursor) params.set('cursor', currentCursor)
if (statusFilter) params.set('status', statusFilter)

const response = await fetch(`/assets?${params}`)
```

---

## Migration Checklist

For each list view in the app:

1. Remove `page` state variable and any `total_items`/`total_pages`/`current_page` usage
2. Add `currentCursor` and `cursorStack` state
3. Update the API call to send `cursor` instead of `page`
4. Update response handling to read `next_cursor` and `has_next_page` instead of `total_items`/`total_pages`
5. Replace the pagination component (numbered pages → Prev/Next buttons)
6. Remove any "Showing X of Y results" or "Page X of Y" text
7. Ensure filter/sort changes call `resetPagination()`
8. Keep "Rows per page" selector — it still works via `page_size`

---

## Edge Cases

- **Empty results**: `items` is `[]`, `count` is `0`, `next_cursor` is `null`, `has_next_page` is `false`. Show "No results found" state.
- **Invalid cursor**: Backend returns 400 if cursor is malformed. Catch this and reset to first page.
- **Cursor expiry**: Cursors encode DynamoDB keys, not timestamps — they don't expire. But if the underlying data changes (item deleted), the cursor still works (DynamoDB skips to the next valid key).
- **Browser back/forward**: If using URL params for pagination state, store the cursor in the URL. Otherwise, navigating back will lose position.
