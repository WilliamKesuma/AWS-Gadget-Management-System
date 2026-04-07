---
inclusion: fileMatch
fileMatchPattern: "src/**/*.{ts,tsx}"
---

# Zod & TanStack Form Best Practices

Consolidated guide for Zod schema validation and TanStack Form patterns in React.

Reference: [Zod API](https://zod.dev/api) · [TanStack Form Quick Start](https://tanstack.com/form/latest/docs/framework/react/quick-start) · [Validation Guide](https://tanstack.com/form/latest/docs/framework/react/guides/validation) · [Form Composition](https://tanstack.com/form/latest/docs/framework/react/guides/form-composition)

---

## A. Zod Schema Best Practices

### 1. Schema Definition & Organization

Define schemas at module scope as `const` — never inside component bodies or render functions. Group related schemas in dedicated files (e.g. `schemas/asset.ts`, `schemas/user.ts`).

```ts
// ✅ module scope
const assetSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  cost: z.number().min(0),
})

// ❌ inside a component
function MyForm() {
  const schema = z.object({ ... }) // re-created every render
}
```

### 2. Type Inference

Derive TypeScript types from schemas using `z.infer` — never duplicate types manually alongside schemas.

```ts
const userSchema = z.object({
  name: z.string(),
  email: z.string().email(),
})

type User = z.infer<typeof userSchema>

// For schemas with transforms, use z.input / z.output
type UserInput = z.input<typeof transformedSchema>
type UserOutput = z.output<typeof transformedSchema>
```

### 3. Schema Composition

#### Extend & Merge

Use spread syntax (preferred) or `.extend()` to compose object schemas. Spread is more tsc-efficient and visually explicit about strictness.

```ts
const baseSchema = z.object({ name: z.string() })

// ✅ spread — clear, efficient
const extendedSchema = z.object({
  ...baseSchema.shape,
  age: z.number(),
})

// ✅ .extend() — also fine for simple cases
const extendedSchema = baseSchema.extend({ age: z.number() })
```

#### Pick & Omit

Use `.pick()` and `.omit()` to derive subsets from existing schemas — never redefine fields manually.

```ts
const createSchema = userSchema.omit({ id: true })
const summarySchema = userSchema.pick({ name: true, email: true })
```

#### Partial & Required

Use `.partial()` for patch/update schemas and `.required()` to enforce all fields.

```ts
const updateSchema = userSchema.partial()              // all optional
const patchSchema = userSchema.partial({ name: true }) // only name optional
```

### 4. Refinements

#### `.refine()` — Single Custom Check

Use `.refine()` for a single boolean check with a custom message.

```ts
const passwordSchema = z.string().refine(
  (val) => /[A-Z]/.test(val),
  { message: 'Must contain at least one uppercase letter' },
)
```

#### `.superRefine()` — Multiple Issues

Use `.superRefine()` when you need to add multiple issues or use specific error codes.

```ts
const formSchema = z.object({
  password: z.string(),
  confirm: z.string(),
}).superRefine((data, ctx) => {
  if (data.password !== data.confirm) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Passwords do not match',
      path: ['confirm'],
    })
  }
})
```

#### Rules

- Refinement functions must never throw — return a falsy value to signal failure.
- Use the `path` option to attach errors to specific fields in object schemas.
- Use `abort: true` on a refinement to stop subsequent checks when it fails.
- Prefer `.refine()` for simple checks, `.superRefine()` for multi-issue or path-specific errors.

### 5. Transforms & Pipes

Use `.transform()` to convert parsed data into a different shape. Combine with `.pipe()` for multi-step parse → transform → validate chains.

```ts
// Simple transform
const trimmed = z.string().transform((s) => s.trim())

// Parse → transform → validate
const ageFromString = z.string()
  .transform((s) => Number(s))
  .pipe(z.number().min(0).max(150))
```

#### Coercion

Use `z.coerce` for automatic type coercion from unknown input (e.g. URL search params, form data).

```ts
const filterSchema = z.object({
  limit: z.coerce.number().min(1).max(100).default(20),
  active: z.coerce.boolean().default(false),
})
```

### 6. Discriminated Unions

Use `z.discriminatedUnion()` for tagged unions — it's more efficient than `z.union()` because it checks the discriminator key first.

```ts
const eventSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('click'), x: z.number(), y: z.number() }),
  z.object({ type: z.literal('scroll'), offset: z.number() }),
])
```

### 7. Parsing Strategy

- `safeParse` / `safeParseAsync` — production default. Returns a discriminated result without throwing.
- `parse` — acceptable in controlled contexts (loaders, server handlers with a global error boundary).

```ts
const result = schema.safeParse(input)
if (!result.success) {
  console.error(result.error.issues)
  return
}
// result.data is fully typed
```

### 8. Error Handling

Access structured errors via `ZodError.issues`. Use `.flatten()` for simple field-level error maps or `.format()` for nested structures.

```ts
const result = schema.safeParse(input)
if (!result.success) {
  const flat = result.error.flatten()
  // flat.fieldErrors: { [field]: string[] }
  // flat.formErrors: string[]
}
```

### 9. Defaults & Optionality

- `.default(value)` — fallback when input is `undefined` (short-circuits parsing).
- `.optional()` — allows `undefined`.
- `.nullable()` — allows `null`.
- `.nullish()` — allows both `null` and `undefined`.
- `.catch(value)` — fallback on any validation error (not just `undefined`).

```ts
const configSchema = z.object({
  retries: z.number().default(3),
  timeout: z.number().optional(),
  label: z.string().catch('unknown'),
})
```

### 10. Enums

Use `z.enum()` for string literal unions. Always pass the array directly or use `as const` — never a mutable variable.

```ts
// ✅ correct
const statusSchema = z.enum(['active', 'inactive', 'pending'])

// ✅ also correct with as const
const STATUSES = ['active', 'inactive', 'pending'] as const
const statusSchema = z.enum(STATUSES)

// ❌ wrong — Zod can't infer literal types
const statuses = ['active', 'inactive']
const statusSchema = z.enum(statuses) // type error
```

Use `.exclude()` and `.extract()` to derive sub-enums from existing ones.

### 11. Zod Forbidden Patterns

- ❌ Defining schemas inside component bodies — always module scope
- ❌ Manually duplicating types alongside schemas — use `z.infer`
- ❌ Using `parse` in UI code where errors should be handled gracefully — use `safeParse`
- ❌ Throwing inside `.refine()` / `.superRefine()` callbacks — return falsy or use `ctx.addIssue`
- ❌ Using `z.any()` or `z.unknown()` without narrowing — always refine or pipe into a concrete type
- ❌ Chaining `.extend()` deeply (3+ levels) — use spread syntax for better tsc performance
- ❌ Using `z.union()` when a discriminator key exists — use `z.discriminatedUnion()`

---

## B. TanStack Form Best Practices

### 1. Form Initialization

Use `useForm` for one-off forms. For app-wide consistency with pre-bound UI components, use `createFormHook` + `createFormHookContexts`.

```tsx
import { useForm } from '@tanstack/react-form'

const form = useForm({
  defaultValues: { name: '', age: 0 },
  validators: { onSubmit: formSchema },
  onSubmit: async ({ value }) => { /* ... */ },
})
```

#### `formOptions` for Shared Defaults

When multiple components share the same form shape, extract defaults with `formOptions`:

```tsx
import { formOptions } from '@tanstack/react-form'

const userFormOpts = formOptions({
  defaultValues: { firstName: '', lastName: '' },
})

// In component:
const form = useForm({ ...userFormOpts, onSubmit: /* ... */ })
```

### 2. Validation Strategy

#### Form-Level vs Field-Level

- Prefer form-level validation with a Zod schema for consistent, centralized rules.
- Use field-level validators only for field-specific logic that depends on `fieldApi` (e.g. linked fields, async uniqueness checks).

```tsx
// ✅ form-level — single schema validates everything
const form = useForm({
  defaultValues: { email: '', age: 0 },
  validators: { onSubmit: formSchema },
})

// ✅ field-level — only when field-specific logic is needed
<form.Field
  name="confirm_password"
  validators={{
    onChangeListenTo: ['password'],
    onChange: ({ value, fieldApi }) => {
      if (value !== fieldApi.form.getFieldValue('password')) {
        return 'Passwords do not match'
      }
      return undefined
    },
  }}
/>
```

#### Validation Triggers

| Trigger | When to use |
|---|---|
| `onSubmit` | Default for most forms — validates only on submit |
| `onBlur` | When real-time feedback on field exit is needed |
| `onChange` | When instant feedback per keystroke is needed (use sparingly) |

Default to `onSubmit`. Combine triggers when needed (e.g. `onChange` for instant feedback + `onBlur` for async checks).

#### Async Validation

Use `onChangeAsync` / `onBlurAsync` for server-side checks. Always set `asyncDebounceMs` to avoid excessive network calls.

```tsx
<form.Field
  name="username"
  asyncDebounceMs={500}
  validators={{
    onChangeAsync: async ({ value }) => {
      const taken = await checkUsername(value)
      return taken ? 'Username already taken' : undefined
    },
  }}
/>
```

Synchronous validators run first. Async validators only run if the sync validator passes (unless `asyncAlways: true` is set).

### 3. Linked Fields

Use `onChangeListenTo` / `onBlurListenTo` to re-run a field's validation when another field changes. This avoids stale validation state.

```tsx
<form.Field
  name="confirm_password"
  validators={{
    onChangeListenTo: ['password'],
    onChange: ({ value, fieldApi }) => {
      if (value !== fieldApi.form.getFieldValue('password')) {
        return 'Passwords do not match'
      }
      return undefined
    },
  }}
/>
```

### 4. Listeners (Side Effects)

Use the `listeners` prop for side effects that should fire when a field changes — not for validation. Common use: resetting a dependent field.

```tsx
<form.Field
  name="country"
  listeners={{
    onChange: ({ value }) => {
      form.setFieldValue('province', '')
    },
  }}
/>
```

Available events: `onChange`, `onBlur`, `onMount`, `onSubmit`. Debounce with `onChangeDebounceMs` / `onBlurDebounceMs`.

Form-level listeners are also available for cross-cutting concerns like autosave:

```tsx
const form = useForm({
  listeners: {
    onChange: ({ formApi }) => {
      if (formApi.state.isValid) formApi.handleSubmit()
    },
    onChangeDebounceMs: 1000,
  },
})
```

### 5. Reactivity & Performance

TanStack Form does not re-render on every interaction by default. To access reactive values, use one of two methods:

#### `useStore` — For Component Logic

Use when you need form state in component logic (conditions, derived values). Always provide a selector.

```tsx
import { useStore } from '@tanstack/react-store'

// ✅ selective — only re-renders when firstName changes
const firstName = useStore(form.store, (state) => state.values.firstName)

// ❌ no selector — re-renders on every state change
const store = useStore(form.store)
```

#### `form.Subscribe` — For UI Rendering

Use when you need reactive UI without triggering component-level re-renders.

```tsx
<form.Subscribe
  selector={(state) => [state.canSubmit, state.isSubmitting]}
  children={([canSubmit, isSubmitting]) => (
    <Button type="submit" disabled={!canSubmit} loading={isSubmitting}>
      Submit
    </Button>
  )}
/>
```

#### Rules

- Always provide a `selector` to `useStore` — omitting it causes unnecessary re-renders.
- Use `form.Subscribe` for UI-only reactivity (submit buttons, conditional sections).
- Use `useStore` when you need the value in component logic (not just JSX).
- Do not use `useField` for reactivity — it's designed for use within `form.Field`.

### 6. Displaying Field Errors

Every field must render its own error messages. TanStack Form exposes errors via `field.state.meta.errors` (array of all current errors) and `field.state.meta.errorMap` (errors keyed by trigger).

```tsx
// ✅ basic pattern — render all errors for the field
{!field.state.meta.isValid && (
  <em role="alert">{field.state.meta.errors.join(', ')}</em>
)}

// ✅ trigger-specific — show only onChange errors
{field.state.meta.errorMap['onChange'] && (
  <em role="alert">{field.state.meta.errorMap['onChange']}</em>
)}
```

Errors can be strings or structured objects (matching the return type of your validator). When using Zod at the form level, errors are automatically routed to the correct field by path.

#### Rules

- Always render errors adjacent to the field they belong to — never collect all errors in a single block.
- Gate error display on `isTouched` or `isValid` to avoid showing errors before user interaction.
- Use `role="alert"` on error elements for screen reader accessibility.
- Errors from form-level validators and field-level validators are merged into the same `errors` array.

---

### 7. Field State Metadata

Each field exposes metadata via `field.state.meta`:

| Property | Meaning |
|---|---|
| `isTouched` | `true` once the user changes or blurs the field |
| `isDirty` | `true` once the field value changes (persistent — stays true even if reverted) |
| `isPristine` | Opposite of `isDirty` |
| `isBlurred` | `true` once the field loses focus |
| `isDefaultValue` | `true` when current value equals the default |
| `isValid` | `true` when no validation errors exist |
| `isValidating` | `true` during async validation |
| `errors` | Array of current error messages/objects |
| `errorMap` | Errors keyed by trigger (`onChange`, `onBlur`, `onSubmit`) |

For non-persistent dirty checking (like React Hook Form), combine: `!field.state.meta.isDefaultValue`.

### 8. Array Fields

Use `mode="array"` on the parent field. Access items via bracket notation. Mutate with field helper methods.

```tsx
<form.Field name="items" mode="array">
  {(field) => (
    <>
      {field.state.value.map((_, i) => (
        <form.Field key={i} name={`items[${i}].name`}>
          {(subField) => (
            <Input
              value={subField.state.value}
              onChange={(e) => subField.handleChange(e.target.value)}
            />
          )}
        </form.Field>
      ))}
      <Button type="button" onClick={() => field.pushValue({ name: '' })}>
        Add Item
      </Button>
    </>
  )}
</form.Field>
```

#### Array Mutation Methods

| Method | Purpose |
|---|---|
| `pushValue(value)` | Append an item |
| `removeValue(index)` | Remove item at index |
| `swapValues(indexA, indexB)` | Swap two items |
| `moveValue(from, to)` | Move item from one index to another |
| `insertValue(index, value)` | Insert at specific index |
| `replaceValue(index, value)` | Replace item at index |
| `clearValues()` | Remove all items |

### 9. Form Submission

#### Standard Pattern

```tsx
<form
  onSubmit={(e) => {
    e.preventDefault()
    e.stopPropagation()
    form.handleSubmit()
  }}
>
```

#### Submission Meta

Pass additional context to `onSubmit` via `onSubmitMeta`:

```tsx
const form = useForm({
  onSubmitMeta: { action: null as 'save' | 'publish' | null },
  onSubmit: async ({ value, meta }) => {
    if (meta.action === 'publish') { /* ... */ }
  },
})

// In JSX:
<Button onClick={() => form.handleSubmit({ action: 'publish' })}>Publish</Button>
```

#### Transformed Values

TanStack Form passes raw input values to `onSubmit`, not Zod-transformed output. Parse inside `onSubmit` if you need transforms:

```tsx
onSubmit: ({ value }) => {
  const parsed = schema.parse(value) // now has transformed types
}
```

### 10. Reset Handling

When using `<button type="reset">`, always prevent the native HTML reset to avoid unexpected behavior:

```tsx
<Button
  type="button"
  onClick={() => form.reset()}
>
  Reset
</Button>
```

### 11. Form Composition

#### Passing Form to Children

Pass the `form` instance as a prop to sub-components — never re-instantiate `useForm` in children.

#### `withForm` for Large Forms

Use `withForm` to break large forms into smaller pieces with full type safety:

```tsx
const AddressSection = withForm({
  defaultValues: { street: '', city: '', zip: '' },
  render: function Render({ form }) {
    return (
      <form.Field name="street">
        {(field) => <Input value={field.state.value} onChange={...} />}
      </form.Field>
    )
  },
})

// Usage:
<AddressSection form={form} />
```

Note: use `function Render` (named function expression) to avoid ESLint hook errors.

### 12. Setting Field Errors from Form Validators

Return `{ fields: { ... } }` from form-level validators to set errors on specific fields (useful for server-side validation):

```tsx
validators: {
  onSubmitAsync: async ({ value }) => {
    const errors = await validateOnServer(value)
    if (errors) {
      return {
        form: 'Server validation failed',
        fields: {
          email: 'Email already registered',
          'address.zip': 'Invalid ZIP code',
        },
      }
    }
    return null
  },
}
```

### 13. TanStack Form Forbidden Patterns

- ❌ `useStore(form.store)` without a selector — causes re-renders on every state change
- ❌ `useField` for reactivity outside `form.Field` — use `useStore` instead
- ❌ Re-instantiating `useForm` in child components — pass the form instance as a prop
- ❌ Using `onRowClick` or `onClick` for form submission — use `form.handleSubmit()` in the `onSubmit` handler
- ❌ Defining `defaultValues` dynamically inside the render cycle — extract to module scope or `useMemo`
- ❌ Mixing `validatorAdapter` / `@tanstack/zod-form-adapter` — deprecated, pass schemas directly to `validators`
- ❌ Using `type="reset"` without `event.preventDefault()` — causes native HTML reset
- ❌ Conditionally calling `useForm` — always call it, use `enabled` or conditional rendering instead
