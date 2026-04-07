# Architecture Protocol

Consolidated guide for Role-Based Access Control (RBAC) and Error Feedback.

---

## A. Role-Based Access Control (RBAC)

### Stack
- Roles: `UserRole` type from `src/lib/models/types.ts`
- Permissions: `src/lib/permissions.ts` — all role checks, ownership checks, and domain permission functions
- Auth provider: AWS Cognito via `aws-amplify`
- Role source: Cognito ID token — `cognito:groups` claim (or `custom:role` if using a custom attribute)
- Router: TanStack Router — role is threaded through router context

### 1. Role Extraction

`getCurrentUserRole()` in `src/lib/auth.ts` reads the role from the Cognito session — never from local storage or component state.

Since `UserRole` is a type alias (not an enum), define a runtime constant for the valid values:

```ts
import { fetchAuthSession } from 'aws-amplify/auth'
import type { UserRole } from './models/types'

const USER_ROLES: string[] = ['it-admin', 'management', 'employee', 'finance']

export async function getCurrentUserRole(): Promise<UserRole | null> {
  try {
    const session = await fetchAuthSession()
    const groups = session.tokens?.idToken?.payload['cognito:groups'] as string[] | undefined
    const match = groups?.find((g) => USER_ROLES.includes(g))
    return (match as UserRole) ?? null
  } catch {
    return null
  }
}
```

### 2. Router Context

Extend `MyRouterContext` in `src/routes/__root.tsx` to carry the role:

```ts
import type { UserRole } from '#/lib/models/new/types'

interface MyRouterContext {
  queryClient: QueryClient
  userRole: UserRole | null
}
```

Resolve and attach the role once in `src/routes/_authenticated.tsx` `beforeLoad` so all child routes inherit it without re-fetching:

```ts
beforeLoad: async ({ context, location }) => {
  const isAuth = await isAuthenticated()
  if (!isAuth) {
    throw redirect({ to: '/login', search: { redirectTo: location.href } })
  }
  const userRole = await getCurrentUserRole()
  return { userRole }
},
```

### 3. Permissions Module — `src/lib/permissions.ts`

All role-based visibility, action gating, and ownership checks must go through this module. Never write inline `role === 'x'` comparisons in components or route files.

#### Two Layers

| Layer | Function | Use when |
|---|---|---|
| `hasRole(role, allowed)` | Simple role gate | Route guards, nav visibility, section show/hide — no entity state involved |
| Domain functions (`getAssetDetailPermissions`, etc.) | Role + entity status + ownership | The check depends on runtime state (asset status, issue status, ownership) |

#### `hasRole` — Simple Role Gates

Use `hasRole` directly for checks that only depend on the user's role:

```tsx
import { hasRole } from '#/lib/permissions'

// Button visibility
{hasRole(role, ['it-admin']) && <Button>Add Asset</Button>}

// View switching
if (hasRole(role, ['it-admin', 'management'])) return <AdminView />
return <EmployeeView />
```

#### `isOwner` — Ownership Checks

Use `isOwner` when comparing the current user to a resource owner:

```tsx
import { isOwner } from '#/lib/permissions'

const isAssignee = isOwner(currentUserId, asset?.assignee?.user_id)
```

#### Domain Permission Functions

Use domain functions when the check combines role + entity state + ownership:

```tsx
import { getAssetDetailPermissions } from '#/lib/permissions'

const { showSoftwareRequestsTab, showIssuesTab } = getAssetDetailPermissions({
  role,
  currentUserId,
  assigneeUserId: asset?.assignee?.user_id,
  assetStatus: asset?.status,
})

{showSoftwareRequestsTab && <TabsTrigger value="software-requests">...</TabsTrigger>}
```

#### Available domain functions

| Function | Context | Returns |
|---|---|---|
| `getAssetDetailPermissions` | role, userId, assigneeId, assetStatus | `showSoftwareRequestsTab`, `showIssuesTab`, `showReportIssueButton`, `showRequestSoftwareButton` |
| `getIssueActionPermissions` | role, issueStatus | `canStartRepair`, `canRequestReplacement`, `canSendWarranty`, `canCompleteRepair`, `canManagementReview` |
| `getSoftwareActionPermissions` | role, softwareStatus | `canITAdminReview`, `canManagementReview` |
| `getAssetRowPermissions` | role, assetStatus | `canManagementReview` |
| `getUserRowPermissions` | currentRole, currentUserId, targetUserId, targetRole | `canViewSignatures`, `canToggleStatus` |

### 4. Route-Level Guards

Protect entire routes using `beforeLoad` in the route file. Always use `hasRole()` — never use raw `includes()` or `!==` comparisons.

```ts
import { hasRole } from '#/lib/permissions'

const ALLOWED: UserRole[] = ['it-admin', 'management']

beforeLoad: ({ context }) => {
  if (!hasRole(context.userRole, ALLOWED)) {
    throw redirect({ to: '/unauthorized' })
  }
}
```

For routes using `as any` in `createFileRoute` (nested dynamic routes), cast `context` to access `userRole`:

```ts
beforeLoad: ({ context }) => {
  if (!hasRole((context as { userRole?: UserRole | null }).userRole ?? null, ALLOWED)) {
    throw redirect({ to: '/unauthorized' })
  }
}
```

### 5. Hook for Component-Level Access

`useCurrentUserRole()` in `src/hooks/use-current-user.ts` reads the role from router context via `useRouterState`. No query, no cache, no loading state needed.

```ts
const role = useCurrentUserRole()
```

This is for UI-level show/hide logic only — it is not a security boundary.

### 6. Adding New Permissions

1. If it's a pure role check → use `hasRole` directly, no new function needed.
2. If it combines role + entity state → add a new domain function to `src/lib/permissions.ts` following the existing pattern:
   - Define a `Context` type with the minimal inputs
   - Define a `Permissions` return type with boolean flags
   - Export a pure function that returns the permissions object

### 7. Rules

1. Always resolve the role in `_authenticated.tsx` `beforeLoad` and pass it via router context — never fetch it per-route.
2. Use `beforeLoad` + `hasRole` for route-level access control. Never guard routes inside the component body.
3. Use `useCurrentUserRole()` for UI-level show/hide logic only — it is not a security boundary.
4. Import `UserRole` as a type-only import (`import type`) — it is a type alias, not a runtime value.
5. When redirecting unauthorized users, throw `redirect({ to: '/unauthorized' })` — do not return or navigate imperatively.
6. Define allowed role arrays (`ALLOWED`) as module-scope constants typed as `UserRole[]`, not inline inside `beforeLoad`.

### 8. Forbidden Patterns

- ❌ `role === 'it-admin'` inline in components — use `hasRole(role, ['it-admin'])`
- ❌ `role === 'management' && status === 'X'` inline — use a domain permission function
- ❌ `context.userRole !== 'employee'` in route guards — use `hasRole`
- ❌ `!ALLOWED.includes(context.userRole!)` with non-null assertion — use `hasRole`
- ❌ `const ctx = context as { userRole?: string }` followed by manual includes — use `hasRole` with the typed cast pattern
- ❌ Duplicating permission logic across multiple components — centralize in `permissions.ts`

---

## B. Error Feedback

### Core Principle

Action errors (button clicks, mutations, API calls outside of forms) must be shown using `toast.error()` from `sonner`. Inline `alert-danger` divs are reserved for form validation/submission errors and data-loading failures only.

### 1. Action Errors → Toast

Any error triggered by a user action (assign, cancel, approve, reject, download, etc.) must use `toast.error()`:

```tsx
import { toast } from 'sonner'

mutation.mutate(payload, {
  onSuccess: () => {
    toast.success('Action completed.')
  },
  onError: (err) => {
    if (err instanceof ApiError) {
      toast.error(err.message)
    } else {
      toast.error('An unexpected error occurred. Please try again.')
    }
  },
})
```

Never store action errors in component state (`useState`) and render them as inline `alert-danger` divs.

### 2. Form Errors → Inline

Form validation and submission errors remain inline using `alert-danger` or `<FieldError>`:

- Field-level validation: `<FieldError errors={field.state.meta.errors} />`
- Form submission errors: `<div className="alert-danger">{submitError}</div>`

### 3. Data Loading Errors → Inline

Query errors from `useQuery` (e.g. failed to load asset detail) stay as inline `alert-danger` since they represent a page/section state, not a transient action result:

```tsx
const { data, error } = useAssetDetail(id)

{error && <div className="alert-danger">{(error as Error).message}</div>}
```

### 4. Success Feedback → Toast

All successful actions use `toast.success()`:

```tsx
toast.success('Asset assigned successfully.')
```

### 5. Forbidden Patterns

- ❌ `useState` + `setError` + `<div className="alert-danger">` for action/mutation errors
- ❌ `toast.error()` for form validation errors — use `<FieldError>` instead
- ❌ `toast.error()` for query loading failures — use inline `alert-danger`
- ❌ Missing `onError` callback on mutations — always handle errors
