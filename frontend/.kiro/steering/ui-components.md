# UI Components & Patterns Protocol

Consolidated guide for Shadcn UI, Table Row Actions, Filter UI, and Formatting.

---

## A. Shadcn UI Component Implementation

LLM Documentation: https://ui.shadcn.com/llms.txt

1. Inspect the `/src/component/ui` directory to identify existing Shadcn components.
2. Implement the available Shadcn component if it satisfies the structural and functional requirements of the use case.
3. If the required component is absent, construct a custom component strictly adhering to Shadcn design principles, styling conventions, and architecture.

### Semantic Status Colors

The project defines three semantic status color tokens in `src/styles.css`. Always use these instead of raw Tailwind color utilities for status/feedback UI.

#### CSS Variables (light + dark aware)

| Token | Purpose |
|---|---|
| `--info` / `--info-foreground` / `--info-subtle` | Informational states |
| `--warning` / `--warning-foreground` / `--warning-subtle` | Warning states |
| `--danger` / `--danger-foreground` / `--danger-subtle` | Destructive / error states |

These are registered in `@theme inline` as `--color-info`, `--color-warning`, `--color-danger` etc., making them available as Tailwind utilities: `bg-info`, `text-info`, `border-warning`, `bg-danger-subtle`, etc.

#### Pre-built Utility Classes

```tsx
// Inline text color
<span className="text-info">Informational</span>
<span className="text-warning">Warning</span>
<span className="text-danger">Danger</span>

// Small status badges — use the Badge component with semantic variants
import { Badge } from '#/components/ui/badge'

<Badge variant="info">Active</Badge>
<Badge variant="warning">Pending</Badge>
<Badge variant="danger">Rejected</Badge>

// Alert / callout blocks
<div className="alert-info">This is an info message.</div>
<div className="alert-warning">This is a warning message.</div>
<div className="alert-danger">This is a danger message.</div>
```

#### Rules

- Never use raw Tailwind colors (e.g. `text-blue-500`, `bg-red-100`) for status feedback — always use the semantic tokens above.
- For status badges, use the `Badge` component with `variant="info"`, `variant="warning"`, or `variant="danger"` — never use raw `<span>` with manual status classes.
- `--danger` mirrors `--destructive` semantically — prefer `--danger` for status display and `--destructive` for Shadcn form/button destructive variants.

### Button Rules

1. Buttons must never contain icons — text-only labels at all times.
2. Use the `loading` prop to indicate a loading/pending state instead of manually swapping content or adding a spinner.

```tsx
// ✅ correct — text-only, loading prop for pending state
<Button loading={isPending}>Submit</Button>

// ❌ wrong — icon inside button
<Button><Loader2 className="animate-spin size-4 mr-2" />Submitting...</Button>

// ❌ wrong — icon as decoration
<Button><Plus className="size-4 mr-1" />Add Item</Button>
```

#### Forbidden Patterns

- ❌ Any `<Icon>` or SVG component rendered inside a `<Button>`
- ❌ Manual spinner/loader elements inside buttons — use `loading` prop
- ❌ `disabled={isPending}` with a custom spinner — use `loading={isPending}` instead

---

### Focus Ring Clipping in Scrollable Containers

Shadcn inputs use a 3px `ring` on focus that extends outside the element boundary. When a form is placed inside a scrollable container (`overflow-y-auto`, `overflow-auto`, or `overflow-hidden`), the ring gets clipped on the edges.

Always apply the negative-margin + padding pattern on the scrollable wrapper:

```tsx
// ✅ correct — ring is fully visible
<div className="overflow-y-auto -mx-1 px-1">
  <MyForm />
</div>

// ❌ wrong — ring is clipped on left/right edges
<div className="overflow-y-auto">
  <MyForm />
</div>
```

This applies to any scrollable container that holds focusable elements: `DialogContent` wrappers, sidebar panels, card bodies with `overflow-auto`, etc.

### Dialog Action Buttons

All action buttons (submit, confirm, approve/reject, cancel, etc.) in a Dialog must be placed inside `<DialogFooter>`. They must never live inside the scrollable content area.

If the action requires additional input fields (e.g. a remarks textarea before confirming), those fields should also be placed inside `<DialogFooter>` above the buttons so they remain visible without scrolling.

```tsx
// ✅ correct — actions pinned at the bottom
<DialogContent>
  <DialogHeader>…</DialogHeader>
  <div className="overflow-y-auto -mx-1 px-1">
    {/* scrollable content */}
  </div>
  <DialogFooter>
    <Button variant="outline" onClick={onCancel}>Cancel</Button>
    <Button onClick={onConfirm}>Confirm</Button>
  </DialogFooter>
</DialogContent>

// ❌ wrong — buttons scroll away with content
<DialogContent>
  <DialogHeader>…</DialogHeader>
  <div className="overflow-y-auto -mx-1 px-1">
    {/* scrollable content */}
    <Button onClick={onConfirm}>Confirm</Button>
  </div>
</DialogContent>
```

### Dialog Form Pattern

When a Dialog contains a TanStack Form, the `<form>` element wraps only the field content — not the footer. Action buttons in `<DialogFooter>` live outside the `<form>` and trigger submission programmatically via `form.handleSubmit()`.

This keeps the footer pinned outside the scrollable area while still supporting form validation and submission.

#### Structure

```tsx
<Dialog open={open} onOpenChange={onOpenChange}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>…</DialogTitle>
      <DialogDescription>…</DialogDescription>
    </DialogHeader>
    <form
      onSubmit={(e) => {
        e.preventDefault()
        e.stopPropagation()
        form.handleSubmit()
      }}
    >
      <FieldGroup>
        {/* form fields here */}
      </FieldGroup>
    </form>
    <DialogFooter>
      <Button variant="outline" type="button" onClick={() => onOpenChange(false)}>
        Cancel
      </Button>
      <form.Subscribe
        selector={(s) => [s.canSubmit]}
        children={([canSubmit]) => (
          <Button
            type="button"
            onClick={() => form.handleSubmit()}
            disabled={!canSubmit}
            loading={mutation.isPending}
          >
            Submit
          </Button>
        )}
      />
    </DialogFooter>
  </DialogContent>
</Dialog>
```

#### Rules

- The `<form>` element wraps only `<FieldGroup>` and its fields — never the `<DialogFooter>`.
- Cancel and submit buttons are placed in `<DialogFooter>`, outside the `<form>`.
- The submit button uses `type="button"` with `onClick={() => form.handleSubmit()}` — not `type="submit"`.
- Use `form.Subscribe` to read `canSubmit` for disabling the button and the mutation's `isPending` for the `loading` prop.

#### Forbidden Patterns

- ❌ `<form>` wrapping the entire `<DialogContent>` including `<DialogFooter>`
- ❌ Submit button with `type="submit"` inside `<DialogFooter>` when the `<form>` is a sibling
- ❌ Placing action buttons inside the `<form>` / scrollable area instead of `<DialogFooter>`

---

## B. Table Row Actions

### Core Principle

Every data table row has a maximum of 2 action buttons:

1. A "View Details" button/link that navigates to the detail page
2. A dropdown menu (⋯) button that contains all other actions for that row

All item-specific actions (assign, cancel, approve, reject, delete, etc.) live inside the dropdown menu — never as standalone buttons in the row.

### 1. Row Action Column

The last column in every table is the actions column. It renders:

```tsx
<div className="flex items-center justify-end gap-2">
  <Button asChild variant="ghost" size="icon">
    <Link to="/assets/$asset_id" params={{ asset_id: row.original.asset_id }}>
      <Eye className="size-4" />
    </Link>
  </Button>
  <DropdownMenu>
    <DropdownMenuTrigger asChild>
      <Button variant="ghost" size="icon">
        <MoreHorizontal className="size-4" />
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end">
      {/* All actions here */}
    </DropdownMenuContent>
  </DropdownMenu>
</div>
```

### 2. Conditional Menu Items

Render dropdown menu items conditionally based on user role and item state. If no actions are available for the current user/state, hide the dropdown trigger entirely — only show the view button.

### 3. Row Click Navigation

Never use `onRowClick` on `<DataTable>` to navigate to a detail page. Navigation to the detail view must only happen via the explicit "View Details" eye icon button in the actions column.

### 4. Forbidden Patterns

- ❌ More than 2 buttons visible per row
- ❌ Action buttons (assign, cancel, delete, etc.) rendered directly in the row outside the dropdown
- ❌ Multiple standalone buttons per row beyond view + dropdown
- ❌ `onRowClick` used to navigate to a detail page — use the eye icon button instead

---

## C. Filter UI

### Core Principle

All filter controls must live inside a **Dialog** by default. The dialog opens via a "Filters" button in the page toolbar. Filters are edited as a local draft and applied on explicit user action ("Apply Filters"), not on every keystroke.

### 1. Default Behavior

- Every filterable list page uses a **filter Dialog** to house its filter fields.
- The dialog contains local draft state. Changes are committed to the URL search params only when the user clicks "Apply Filters".
- A "Reset" button inside the dialog clears all draft fields back to their defaults.

### 2. Exceptions

Fields may live **outside** the dialog (e.g. in the toolbar) only when the user explicitly requests it. Common examples:

- A search input for a high-frequency field (e.g. model name)
- Category tabs or segmented controls that act as primary navigation

If not explicitly told otherwise, **all filter fields go inside the dialog**.

### 3. Toolbar Pattern

The toolbar row sits between the page header and the data table. It contains:

1. Any explicitly external filter controls (search input, tabs, etc.)
2. A "Filters" button that opens the dialog, showing a badge with the count of active dialog filters
3. A "Clear all" button (visible only when any filter is active) that resets all filters — both dialog and external

```tsx
<div className="flex items-center gap-3 mt-3">
  {/* External controls here */}
  <Button variant="outline" size="sm" onClick={() => setFilterOpen(true)}>
    <Filter className="size-4 mr-1.5" />
    Filters
    {dialogFilterCount > 0 && (
      <Badge variant="default" size="sm" className="ml-1.5">
        {dialogFilterCount}
      </Badge>
    )}
  </Button>
  {hasAnyFilter && (
    <Button variant="ghost" size="sm" onClick={clearAllFilters}>
      <X className="size-4 mr-1" />
      Clear all
    </Button>
  )}
</div>
```

### 4. URL Sync

All filter state (both dialog and external) must be synced to URL search params via `validateSearch` with a Zod schema. This ensures filters persist on refresh and are shareable. When any filter changes, call `resetPagination()` to return to the first page (see `cursor-pagination.md`).

### 5. Forbidden Patterns

- ❌ Inline filter rows with many controls spread across the page
- ❌ Filters that fire API calls on every keystroke without debounce (for text inputs outside the dialog, use `useDebounce`)
- ❌ Filter state stored only in component state without URL sync

---

## D. Formatting

### Utilities

All formatters live in `src/lib/utils.ts`. Always import from there — never use `date-fns`, `Intl`, or inline formatting logic in components.

| Function | Output | Use for |
|---|---|---|
| `formatDate(value)` | `"23 Mar 2025"` | Displaying any date (ISO string, timestamp, or Date object) |
| `formatNumber(value)` | `"20.000.000"` | Displaying any integer/currency number |
| `parseFormattedNumber(str)` | `number \| undefined` | Parsing a dot-grouped string back to a raw number |

### 1. Displaying Dates

Always use `formatDate` — never `date-fns` `format`, `toLocaleDateString`, or manual string slicing.

```tsx
import { formatDate } from '#/lib/utils'

// ✅ correct
<span>{formatDate(user.created_at)}</span>          // "23 Mar 2025"
<span>{formatDate(asset.assignment_date) || '—'}</span>

// ❌ wrong
<span>{format(new Date(user.created_at), 'MMM d, yyyy')}</span>
<span>{new Date(asset.purchase_date).toLocaleDateString()}</span>
```

### 2. Displaying Numbers

Always use `formatNumber` for any integer or currency value rendered in the UI.

```tsx
import { formatNumber } from '#/lib/utils'

// ✅ correct
<span>{formatNumber(asset.cost)}</span>             // "24.975.000"
<span>{formatNumber(stats.total_assets)}</span>     // "1.284"

// ❌ wrong
<span>{asset.cost.toLocaleString()}</span>
<span>{asset.cost}</span>
```

### 3. Number Form Inputs

Use `NumberInput` from `#/components/ui/input` for any form field that accepts a numeric value. It live-formats as the user types and preserves cursor position.

```tsx
import { NumberInput } from '#/components/ui/input'

// ✅ correct — inside a TanStack Form field
<NumberInput
  id={field.name}
  value={field.state.value}
  onChange={(v) => field.handleChange(v ?? 0)}
  onBlur={field.handleBlur}
  aria-invalid={isInvalid}
/>

// ❌ wrong
<Input type="number" ... />
<input type="number" ... />
```

`NumberInput` props:
- `value: number | undefined` — raw numeric value (unformatted)
- `onChange: (value: number | undefined) => void` — called with the raw number on every keystroke

### 4. TanStack Table Columns

Apply formatters directly in the `cell` renderer. Never format in the data layer or query `select`.

```tsx
columnHelper.accessor('purchase_date', {
  header: 'PURCHASE DATE',
  cell: (info) => <span>{formatDate(info.getValue()) || '—'}</span>,
})

columnHelper.accessor('cost', {
  header: 'COST',
  cell: (info) => <span>{formatNumber(info.getValue())}</span>,
})
```

### 5. Forbidden Patterns

- ❌ `date-fns` `format()` for display — use `formatDate`
- ❌ `toLocaleDateString()` / `toLocaleString()` — use `formatDate` / `formatNumber`
- ❌ `new Intl.NumberFormat(...)` inline — use `formatNumber`
- ❌ `<Input type="number">` for form number fields — use `NumberInput`
- ❌ Raw `{value}` for numeric or date fields in JSX — always pass through the formatter
