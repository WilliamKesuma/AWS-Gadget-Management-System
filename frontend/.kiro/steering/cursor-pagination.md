# Cursor-Based Pagination Protocol

Guide for implementing cursor-based pagination across all list views.

---

## A. API Contract

All list endpoints use DynamoDB cursor-based pagination. There are no page numbers, total counts, or offset parameters.

### Request Parameters

| Parameter | Type | Description |
|---|---|---|
| `page_size` | `number` (optional, default 20, max 100) | Items per page |
| `cursor` | `string` (optional) | Opaque cursor from previous response. Omit for first page. |

### Response Shape

```json
{
  "items": [...],
  "count": 20,
  "next_cursor": "eyJQSyI6ICJBU1NFV...",
  "has_next_page": true
}
```

| Field | Type | Description |
|---|---|---|
| `items` | `T[]` | Page of results |
| `count` | `number` | Number of items in this page |
| `next_cursor` | `string \| null` | Cursor for the next page, `null` on last page |
| `has_next_page` | `boolean` | Whether more pages exist |

### TypeScript Types — `src/lib/models/types.ts`

```ts
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

All list filter types extend `PaginatedAPIFilter`. All list response types use `PaginatedAPIResponse<T>`.

### Notifications Response (special case)

`GET /notifications` also returns `unread_count` alongside the paginated fields.

---

## B. `useCursorPagination` Hook — `src/hooks/use-cursor-pagination.ts`

Every paginated list view must use this hook to manage cursor state. It maintains a cursor stack for backward navigation.

```tsx
import { useCursorPagination } from '#/hooks/use-cursor-pagination'

const {
  currentCursor,   // string | undefined — pass to query hook
  goToNextPage,    // (nextCursor: string) => void
  goToPreviousPage,// () => void
  resetPagination, // () => void — call on filter/sort changes
  canGoPrevious,   // boolean
  pageSize,        // number
} = useCursorPagination(PAGE_SIZE)
```

### Rules

- Call `resetPagination()` whenever filters, sort order, or tabs change.
- Pass `currentCursor` as the cursor argument to query hooks.
- Never store cursors in URL search params — they are opaque local state.
- `page_size` changes should also call `resetPagination()`.

---

## C. Query Hook Signatures

All list query hooks accept `cursor: string | undefined` instead of `page: number`.

```ts
// ✅ correct — cursor-based
useAssets(filters, currentCursor, pageSize)
useAllIssues(filters, currentCursor, pageSize)
useAllSoftwareRequests(filters, currentCursor, pageSize)
useAllReturns(filters, currentCursor, pageSize)
useDisposals(filters, currentCursor, pageSize)
usePendingDisposals(currentCursor, pageSize, history)
usePendingReplacements(currentCursor, pageSize, history)
usePendingSignatures(currentCursor, pageSize)
useReturns(assetId, filters, currentCursor, pageSize)
useSoftwareRequests(assetId, filters, currentCursor, pageSize)
useIssues(assetId, filters, currentCursor, pageSize)
useCategories({ cursor, page_size })
useEmployeeSignatures(employeeId, { cursor, page_size, filters })

// ❌ wrong — page-based (removed)
useAssets(filters, page, pageSize)
```

For non-paginated calls (e.g. fetching all items for a dropdown), pass `undefined` as cursor:

```ts
const { data } = useAssets({ status: 'ASSIGNED' }, undefined, 100)
```

---

## D. Query Key Factory — `src/lib/query-keys.ts`

All list query key factories use `cursor` instead of `page`:

```ts
queryKeys.assets.list({ cursor, page_size, status, ... })
queryKeys.users.list({ cursor, page_size, filters })
queryKeys.categories.list({ cursor, page_size })
```

---

## E. DataTable Component — `src/components/general/DataTable.tsx`

The `DataTable` component renders Prev/Next navigation. It does not support numbered pages, "Showing X of Y", or total counts.

### Props

```ts
interface DataTableProps<TData> {
  columns: ColumnDef<TData, any>[]
  data: TData[]
  pageSize?: number
  entityName?: string
  isLoading?: boolean
  error?: string
  hasNextPage?: boolean
  canGoPrevious?: boolean
  onNextPage?: () => void
  onPreviousPage?: () => void
}
```

### Usage Pattern

```tsx
const {
  currentCursor, goToNextPage, goToPreviousPage,
  resetPagination, canGoPrevious, pageSize,
} = useCursorPagination(PAGE_SIZE)

const { data, isLoading, error } = useAssets(filters, currentCursor, pageSize)

<DataTable
  columns={columns}
  data={data?.items ?? []}
  entityName="assets"
  isLoading={isLoading}
  error={error ? (error as Error).message : undefined}
  pageSize={pageSize}
  hasNextPage={data?.has_next_page ?? false}
  canGoPrevious={canGoPrevious}
  onNextPage={() => data?.next_cursor && goToNextPage(data.next_cursor)}
  onPreviousPage={goToPreviousPage}
/>
```

### Non-Paginated Tables

For tables that show all data without pagination (dashboards, small lists), omit the pagination props:

```tsx
<DataTable
  columns={columns}
  data={items}
  pageSize={items.length || 10}
  entityName="approvals"
  isLoading={isLoading}
/>
```

---

## F. URL Search Params

Pagination state (cursor, cursor stack) is local component state — never stored in URL search params. Only filters, sort order, and tab selection belong in the URL.

```ts
// ✅ correct — no page/cursor in search schema
const searchSchema = z.object({
  tab: z.string().optional(),
  status: StatusSchema.optional(),
  history: z.coerce.boolean().optional(),
})

// ❌ wrong — page in URL
const searchSchema = z.object({
  page: z.coerce.number().min(1).optional(),
  status: StatusSchema.optional(),
})
```

When filters change, call `resetPagination()` to return to the first page:

```tsx
const setSearchAndResetPage = useCallback(
  (updates: Partial<SearchSchema>) => {
    resetPagination()
    setSearch(updates)
  },
  [setSearch, resetPagination],
)
```

---

## G. Tab Components with Internal Pagination

Tab components (`ReturnsTab`, `DisposalsTab`, `SoftwareRequestsTab`) manage their own cursor pagination internally via `useCursorPagination`. They do not accept `page` or `onPageChange` props.

When the parent changes filters via `onSearchChange`, the tab resets pagination using a `useEffect`:

```tsx
useEffect(() => {
  resetPagination()
}, [search.status, search.trigger, resetPagination])
```

---

## H. Infinite Scroll (Notifications)

`useNotifications` uses `useInfiniteQuery` with cursor-based pagination:

```ts
return useInfiniteQuery({
  queryFn: ({ pageParam }) => {
    const params = new URLSearchParams(baseParams)
    if (pageParam) params.set('cursor', pageParam)
    return apiClient<ListNotificationsResponse>(`/notifications?${params}`)
  },
  initialPageParam: undefined as string | undefined,
  getNextPageParam: (lastPage) =>
    lastPage.has_next_page && lastPage.next_cursor
      ? lastPage.next_cursor
      : undefined,
})
```

---

## I. Forbidden Patterns

- ❌ `page` parameter in API calls — use `cursor`
- ❌ `total_items`, `total_pages`, `current_page` in response types — removed
- ❌ `totalCount`, `currentPage`, `onPageChange` props on `DataTable` — removed
- ❌ "Showing X of Y" or "Page X of Y" text — not available with cursor pagination
- ❌ Numbered page links or page number navigation — use Prev/Next only
- ❌ Storing cursor in URL search params — cursors are opaque local state
- ❌ `page` in `validateSearch` Zod schemas — pagination is not URL state
- ❌ `useAssets(filters, page, pageSize)` — second arg is `cursor: string | undefined`, not `page: number`
