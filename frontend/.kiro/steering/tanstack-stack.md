# TanStack Stack Protocol

Consolidated guide for TanStack Router, Query, Table, and Form + Zod.

---

## A. TanStack Router

Documentation: https://tanstack.com/router/latest/docs/framework/react/overview

1. Use `@tanstack/react-router` for all client-side routing with file-based route generation via `@tanstack/router-plugin`.
2. Never manually edit `routeTree.gen.ts` — it is auto-generated and will be regenerated when route files change.
3. Enforce type-safe navigation via `<Link>`, `useNavigate`, `useParams`, `useSearch`. Always pass `from` to `useParams`/`useSearch` for fully inferred types; use `strict: false` only for reusable cross-route components.
4. Define data dependencies using route `loader` functions. Integrate with TanStack Query by calling `queryClient.ensureQueryData` inside loaders to prime the cache before render.
5. Validate and parse search parameters using `validateSearch` with a Zod schema or `zodSearchValidator` — never access raw `search` strings.
6. Implement granular `pendingComponent` and `errorComponent` at the route level. Set `pendingMs` / `pendingMinMs` to avoid flicker on fast connections.
7. Use `beforeLoad` for authentication guards and redirects. Throw `redirect()` to redirect; use `isRedirect()` to re-throw intentional redirects inside try/catch blocks.
8. Pass authentication and shared app state into the router via `router.context` using `createRootRouteWithContext`. Never read React context or call hooks outside of components.
9. Use pathless / layout routes (prefix with `_`) to share layouts and `beforeLoad` guards across route groups without affecting the URL.
10. Leverage `route.lazy()` and `createLazyFileRoute` for code-splitting non-critical routes.
11. Use `<Link preload="intent">` or `router.preloadRoute()` on hover/focus to prefetch route data before navigation.
12. Prefer `router.history.push(search.redirect)` over `router.navigate` when redirecting back to a previously stored URL after login.
13. Never use `router.navigate()` for static destination links in JSX — use `<Link>` instead. Reserve `useNavigate` for programmatic navigation that depends on runtime logic (e.g. post-submit redirects). When attaching a `<Link>` to a Shadcn `Button`, use `asChild`:

```tsx
// ✅ correct — preserves history, native link behaviour
<Button asChild>
  <Link to="/dashboard">Go to dashboard</Link>
</Button>

// ❌ wrong — resets history stack, no native link behaviour
<Button onClick={() => router.navigate({ to: '/dashboard' })}>
  Go to dashboard
</Button>
```

---

## B. TanStack Query

Documentation: https://tanstack.com/query/latest/docs/framework/react/overview

1. Route all async server state through TanStack Query (`useQuery`, `useMutation`). Never use `useEffect` + `fetch`/`axios` for server state.
2. Implement the Query Key Factory pattern centrally in a dedicated `query-keys.ts` file for cache consistency and type safety.
3. Eliminate hardcoded or inline array query keys in UI components — all keys must reference the factory.
4. Execute cache invalidation strictly through the key factory — never use raw string arrays in `invalidateQueries`.
5. Encapsulate all `useQuery` and `useMutation` calls within custom hooks. Never call them directly inside UI components.
6. Configure explicit `staleTime` values. A default of `0` is forbidden unless strictly required. Use `Infinity` for static/reference data.
7. Prefer UI-based optimistic updates (via `variables` + `isPending`) for simple cases. Use `onMutate` / cache manipulation only when multiple components need to reflect the update simultaneously.
8. Always use `onSettled` to trigger `invalidateQueries` after mutations — ensures cache refresh regardless of success or failure.
9. Pre-fetch critical data during routing or hover states using `queryClient.prefetchQuery`.
10. Use `useMutationState` with a `mutationKey` to share pending mutation state across components without a common ancestor.
11. Assign `mutationKey` to all `useMutation` calls that need to be observed or deduplicated across the component tree.
12. Leverage `select` in `useQuery` to derive or transform data at the query level, keeping components free of transformation logic.
13. Use `enabled` to conditionally fire queries — never conditionally call the hook itself.
14. For infinite scroll data, use `useInfiniteQuery` with cursor-based `getNextPageParam`. For standard paginated lists, use `useQuery` with the `useCursorPagination` hook (see `cursor-pagination.md`).

---

## C. TanStack Table

Documentation: https://tanstack.com/table/latest/docs/introduction

1. Use `@tanstack/react-table` for data grid architectures.
2. Isolate the headless UI logic (`useReactTable`) from the structural markup and Shadcn component layers.
3. Memoize `data` and `columns` references using `useMemo` to prevent unnecessary re-renders and reference instability.
4. Extract column definitions (`createColumnHelper`) outside the component render cycle.
5. Delegate heavy data manipulation (pagination, sorting, filtering) to the server for large datasets, passing state to the table via manual configurations.
6. Throttle or debounce rapid state changes, such as global text filtering inputs.

---

## D. TanStack Form + Zod

Documentation:

- https://ui.shadcn.com/docs/forms/tanstack-form
- https://tanstack.com/form/latest/docs/framework/react/guides/basic-concepts
- https://zod.dev/api

### 1. Form Setup

Use `useForm` from `@tanstack/react-form`. Pass the Zod schema directly via the `validators` option — do **not** use `validatorAdapter` or `@tanstack/zod-form-adapter` (deprecated).

```tsx
import { useForm } from '@tanstack/react-form'
import { z } from 'zod'

const formSchema = z.object({
  title: z.string().min(5, 'Title must be at least 5 characters.'),
})

const form = useForm({
  defaultValues: { title: '' },
  validators: {
    onSubmit: formSchema,
  },
  onSubmit: async ({ value }) => { /* ... */ },
})
```

### 2. Schema Definition

Define Zod schemas statically at module scope — never inside the component render cycle.

```tsx
const formSchema = z.object({ /* ... */ })
```

Infer TypeScript types from schemas using `z.infer<typeof formSchema>` when needed.

### 3. Field Markup — Use Shadcn Field Components

Wrap every field in the Shadcn `<Field>`, `<FieldLabel>`, and `<FieldError>` components from `#/components/ui/field`. Do **not** use raw `<div>` + `<Label>` + `<p>` for field layout and errors.

```tsx
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
  FieldDescription,
} from '#/components/ui/field'
```

#### Field pattern

```tsx
<form.Field
  name="title"
  children={(field) => {
    const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid
    return (
      <Field data-invalid={isInvalid}>
        <FieldLabel htmlFor={field.name}>Title</FieldLabel>
        <Input
          id={field.name}
          name={field.name}
          value={field.state.value}
          onBlur={field.handleBlur}
          onChange={(e) => field.handleChange(e.target.value)}
          aria-invalid={isInvalid}
        />
        <FieldDescription>A short description.</FieldDescription>
        {isInvalid && <FieldError errors={field.state.meta.errors} />}
      </Field>
    )
  }}
/>
```

#### Rules

- Always derive `isInvalid` as `field.state.meta.isTouched && !field.state.meta.isValid`.
- Always set `data-invalid={isInvalid}` on `<Field>`.
- Always set `aria-invalid={isInvalid}` on the form control (`<Input>`, `<SelectTrigger>`, `<Checkbox>`, etc.).
- Always render errors via `<FieldError errors={field.state.meta.errors} />` — never manually stringify errors.
- Wrap all fields in `<FieldGroup>` for consistent spacing.

### 4. Validation Triggers

Set validation mode at the form level via `validators`:

```tsx
validators: {
  onSubmit: formSchema,   // validate on submit (default)
}
```

Default to `onSubmit` for most forms. Use `onBlur` or `onChange` only when real-time feedback is needed.

### 5. Form Submission

Intercept native form submissions:

```tsx
<form onSubmit={(e) => {
  e.preventDefault()
  e.stopPropagation()
  form.handleSubmit()
}}>
```

Manage submission state via `form.Subscribe` or `form.state.isSubmitting` to disable the submit button.

### 6. Select Fields

Use `onValueChange` directly with `field.handleChange`:

```tsx
<Select name={field.name} value={field.state.value} onValueChange={field.handleChange}>
  <SelectTrigger id={field.name} aria-invalid={isInvalid}>
    <SelectValue placeholder="Select" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="option1">Option 1</SelectItem>
  </SelectContent>
</Select>
```

### 7. Dynamic Array Fields

Use `mode="array"` on the parent field. Access items via bracket notation `fieldName[index].property`. Use `field.pushValue`, `field.removeValue`, and `field.swapValues` for mutations.

### 8. Form Composition

Compose large forms from sub-components by passing the `form` instance as a prop — never re-instantiate `useForm` in child components.

### 9. Async Validation

Support async validation via async validator functions on `onChange`/`onBlur`. Use `asyncDebounceMs` to debounce and avoid excessive network calls.

### 10. Forbidden Patterns

- ❌ `validatorAdapter: zodValidator()` — deprecated, do not use
- ❌ `@tanstack/zod-form-adapter` — deprecated, do not import
- ❌ Raw `<div>` + `<Label>` + `<p className="text-danger">` for field layout — use `<Field>` + `<FieldLabel>` + `<FieldError>`
- ❌ `field.state.meta.errors[0]?.toString()` — errors are objects, use `<FieldError errors={...} />`
- ❌ Per-field `validators: { onBlur: schema.shape.fieldName }` — prefer form-level validation
- ❌ Missing `aria-invalid` on form controls
- ❌ Missing `data-invalid` on `<Field>`
