import { lazy, Suspense, useMemo, useState } from 'react'
import {
  Search,
  MoreHorizontal,
  UserX,
  UserCheck,
  FileSignature,
} from 'lucide-react'
import { toast } from 'sonner'
import { createFileRoute, redirect, useNavigate } from '@tanstack/react-router'
import { z } from 'zod'
import { createColumnHelper, type ColumnDef } from '@tanstack/react-table'
import {
  getBaseMeta,
  getPageMeta,
  getCanonicalLink,
  type SeoPageInput,
} from '../../lib/seo'
import { Button } from '#/components/ui/button'
import { DataTable } from '#/components/general/DataTable'
import { Tabs, TabsList, TabsTrigger } from '#/components/ui/tabs'
import { Input } from '#/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '#/components/ui/select'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '#/components/ui/dropdown-menu'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '#/components/ui/dialog'
import { useUsers } from '#/hooks/use-users'
import { useCurrentUserId, useCurrentUserRole } from '#/hooks/use-current-user'
import { getUserRowPermissions, hasRole } from '#/lib/permissions'
import { useDebounce } from '#/hooks/use-debounce'

// Lazy-loaded components
const CreateUserDialog = lazy(() =>
  import('#/components/users/CreateUserDialog').then((m) => ({
    default: m.CreateUserDialog,
  })),
)
const EmployeeSignaturesSection = lazy(() =>
  import('#/components/assets/EmployeeSignaturesSection').then((m) => ({
    default: m.EmployeeSignaturesSection,
  })),
)

import type { UserRole, UserStatus, UserItem } from '#/lib/models/types'
import { UserStatusSchema } from '#/lib/models/types'
import { formatDate } from '#/lib/utils'
import { UserRoleLabels } from '#/lib/models/labels'

const USERS_SEO = {
  title: 'User Management',
  description:
    'Manage organization directory members, assign security roles, control access levels, and monitor user account activity.',
  path: '/users',
} satisfies SeoPageInput

const USERS_ALLOWED: UserRole[] = ['it-admin']

const usersSearchSchema = z.object({
  status: z.union([UserStatusSchema, z.literal('all')]).optional(),
  name: z.string().optional(),
  role: z.string().optional(),
})

export const Route = createFileRoute('/_authenticated/users')({
  validateSearch: (raw: Record<string, unknown>) =>
    usersSearchSchema.parse(raw),
  beforeLoad: ({ context }) => {
    if (!hasRole(context.userRole, USERS_ALLOWED)) {
      throw redirect({ to: '/unauthorized' })
    }
  },
  component: UsersPage,
  head: () => ({
    meta: [
      ...getBaseMeta(),
      { name: 'robots', content: 'noindex, nofollow' },
      ...getPageMeta(USERS_SEO),
    ],
    links: [getCanonicalLink(USERS_SEO.path)],
  }),
})

const columnHelper = createColumnHelper<UserItem>()

function UserActionsCell({ user }: { user: UserItem }) {
  const [openDeactivate, setOpenDeactivate] = useState(false)
  const [openReactivate, setOpenReactivate] = useState(false)
  const [openSignatures, setOpenSignatures] = useState(false)

  const {
    deactivateUser: { mutateAsync: deactivateAsync, isPending: isDeactivating },
    reactivateUser: { mutateAsync: reactivateAsync, isPending: isReactivating },
  } = useUsers()

  const currentUserId = useCurrentUserId()
  const currentRole = useCurrentUserRole()
  const isActive = user.status === 'active'
  const isPending = isDeactivating || isReactivating

  const { canViewSignatures, canToggleStatus } = getUserRowPermissions({
    currentRole,
    currentUserId,
    targetUserId: user.user_id,
    targetRole: user.role,
  })
  const hasActions = canViewSignatures || canToggleStatus

  const handleDeactivate = async () => {
    try {
      await deactivateAsync(user.user_id)
      toast.success(`User "${user.fullname}" deactivated successfully.`)
      setOpenDeactivate(false)
    } catch (err: any) {
      toast.error(err?.message ?? 'Failed to deactivate user.')
    }
  }

  const handleReactivate = async () => {
    try {
      await reactivateAsync(user.user_id)
      toast.success(`User "${user.fullname}" reactivated successfully.`)
      setOpenReactivate(false)
    } catch (err: any) {
      toast.error(err?.message ?? 'Failed to reactivate user.')
    }
  }

  if (!hasActions) return null

  return (
    <>
      <div className="flex items-center justify-end">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <MoreHorizontal className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {canViewSignatures && (
              <DropdownMenuItem onClick={() => setOpenSignatures(true)}>
                <FileSignature className="size-4" />
                View Signatures
              </DropdownMenuItem>
            )}
            {canToggleStatus && isActive && (
              <DropdownMenuItem onClick={() => setOpenDeactivate(true)}>
                <UserX className="size-4" />
                Deactivate
              </DropdownMenuItem>
            )}
            {canToggleStatus && !isActive && (
              <DropdownMenuItem onClick={() => setOpenReactivate(true)}>
                <UserCheck className="size-4" />
                Reactivate
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <Dialog open={openDeactivate} onOpenChange={setOpenDeactivate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Deactivate User?</DialogTitle>
            <DialogDescription className="pt-2 font-medium">
              Are you sure you want to deactivate{' '}
              <strong className="text-foreground">{user.fullname}</strong>? This
              user will no longer be able to log in or access the system.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="pt-4 gap-2">
            <Button
              variant="outline"
              onClick={() => setOpenDeactivate(false)}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeactivate}
              disabled={isPending}
              loading={isDeactivating}
            >
              {isDeactivating ? 'Deactivating...' : 'Yes, Deactivate'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={openReactivate} onOpenChange={setOpenReactivate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reactivate User?</DialogTitle>
            <DialogDescription className="pt-2 font-medium">
              Are you sure you want to reactivate{' '}
              <strong className="text-foreground">{user.fullname}</strong>? This
              user will regain access to the system.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="pt-4 gap-2">
            <Button
              variant="outline"
              onClick={() => setOpenReactivate(false)}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={handleReactivate}
              disabled={isPending}
              loading={isReactivating}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              {isReactivating ? 'Reactivating...' : 'Yes, Reactivate'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={openSignatures} onOpenChange={setOpenSignatures}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Handover Signatures — {user.fullname}</DialogTitle>
            <DialogDescription>
              Historical handover signatures for this employee.
            </DialogDescription>
          </DialogHeader>
          <div className="overflow-y-auto -mx-1 px-1">
            <Suspense fallback={<div className="py-8 text-center text-sm text-muted-foreground">Loading signatures...</div>}>
              <EmployeeSignaturesSection employeeId={user.user_id} />
            </Suspense>
          </div>
          <DialogFooter showCloseButton />
        </DialogContent>
      </Dialog>
    </>
  )
}

const columns: ColumnDef<UserItem, any>[] = [
  columnHelper.accessor('fullname', {
    header: 'USER',
    cell: (info) => {
      const user = info.row.original
      const initials = user.fullname
        ? user.fullname
          .split(' ')
          .map((n) => n[0])
          .join('')
          .toUpperCase()
        : '??'

      const bgColors = [
        'bg-blue-100 text-blue-700',
        'bg-orange-100 text-orange-700',
        'bg-purple-100 text-purple-700',
        'bg-emerald-100 text-emerald-700',
        'bg-rose-100 text-rose-700',
      ]

      const colorIndex =
        user.user_id
          .split('')
          .reduce((acc, char) => acc + char.charCodeAt(0), 0) % bgColors.length
      const bgColor = bgColors[colorIndex]

      return (
        <div className="flex items-center gap-4 py-1">
          <div
            className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold ${bgColor}`}
          >
            {initials.slice(0, 2)}
          </div>
          <div className="flex flex-col">
            <span className="font-semibold text-sm">{user.fullname}</span>
            <span className="text-xs text-muted-foreground font-medium">
              {user.email}
            </span>
          </div>
        </div>
      )
    },
  }),
  columnHelper.accessor('role', {
    header: 'ROLE',
    cell: (info) => (
      <span className="text-sm font-medium">
        {UserRoleLabels[info.getValue() as UserRole]}
      </span>
    ),
  }),
  columnHelper.accessor('status', {
    header: 'STATUS',
    cell: (info) => {
      const status = info.getValue()
      let dotColor = 'bg-slate-300'
      if (status === 'active') dotColor = 'bg-emerald-500'
      if (status === 'inactive') dotColor = 'bg-rose-500'

      let textColor = 'text-success'
      if (status === 'active') textColor = 'text-success'
      if (status === 'inactive') textColor = 'text-danger'

      return (
        <div
          className={`flex items-center gap-2 text-sm font-bold ${textColor}`}
        >
          <div className={`h-2 w-2 rounded-full ${dotColor}`} />
          {status.toUpperCase()}
        </div>
      )
    },
  }),
  columnHelper.accessor('created_at', {
    header: 'CREATED',
    cell: (info) => (
      <span className="text-xs font-medium text-muted-foreground">
        {formatDate(info.getValue()) || '—'}
      </span>
    ),
  }),
  columnHelper.display({
    id: 'actions',
    header: '',
    cell: (info) => <UserActionsCell user={info.row.original} />,
  }),
]

const PAGE_SIZE = 10

function UsersPage() {
  const navigate = useNavigate({ from: '/users' })
  const search = Route.useSearch()

  const status = search.status ?? 'all'
  const nameRaw = search.name ?? ''
  const role = search.role

  const debouncedName = useDebounce(nameRaw, 400)

  const {
    data,
    isLoading,
    error,
    setNameSearch,
    setRoleFilter,
    setStatusFilter,
    pageSize,
    hasNextPage,
    canGoPrevious,
    goToNextPage,
    goToPreviousPage,
  } = useUsers(PAGE_SIZE)

  // Sync URL state into the hook
  useMemo(() => {
    setNameSearch(debouncedName)
    setRoleFilter((role ?? 'all') as UserRole | 'all')
    setStatusFilter((status === 'all' ? 'all' : status) as UserStatus | 'all')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedName, role, status])

  const tableColumns = useMemo(() => columns, [])

  function setSearchAndResetPage(
    updates: Partial<z.infer<typeof usersSearchSchema>>,
  ) {
    void navigate({ search: { ...search, ...updates } })
  }

  function clearAllFilters() {
    void navigate({ search: {} })
  }

  const hasAnyFilter = !!role || !!nameRaw

  return (
    <main className="page-base">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="page-title">Users</h1>
          <p className="page-subtitle">
            Manage organization directory members, assign security roles, and
            monitor account access levels.
          </p>
        </div>
        <div className="mt-2">
          <Suspense fallback={null}>
            <CreateUserDialog />
          </Suspense>
        </div>
      </div>

      <Tabs
        value={status}
        onValueChange={(v) =>
          setSearchAndResetPage({ status: v as UserStatus | 'all' })
        }
        className="mt-4"
      >
        <TabsList variant="line">
          <TabsTrigger value="all">All Users</TabsTrigger>
          <TabsTrigger value="active">Active</TabsTrigger>
          <TabsTrigger value="inactive">Inactive</TabsTrigger>
        </TabsList>
      </Tabs>

      <div className="flex items-center gap-3 mt-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by name..."
            aria-label="Search users by name"
            className="pl-9 w-[220px]"
            value={nameRaw}
            onChange={(e) =>
              setSearchAndResetPage({ name: e.target.value || undefined })
            }
          />
        </div>

        <Select
          value={role ?? 'all'}
          onValueChange={(v) =>
            setSearchAndResetPage({ role: v === 'all' ? undefined : v })
          }
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="All roles" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All roles</SelectItem>
            {(Object.keys(UserRoleLabels) as UserRole[]).map((value) => (
              <SelectItem key={value} value={value}>
                {UserRoleLabels[value]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {hasAnyFilter && (
          <Button variant="ghost" size="sm" onClick={clearAllFilters}>
            Clear all
          </Button>
        )}
      </div>

      <DataTable
        columns={tableColumns}
        data={data?.items ?? []}
        entityName="users"
        pageSize={pageSize}
        isLoading={isLoading}
        error={error ? (error as Error).message : undefined}
        hasNextPage={hasNextPage}
        canGoPrevious={canGoPrevious}
        onNextPage={() => data?.next_cursor && goToNextPage(data.next_cursor)}
        onPreviousPage={goToPreviousPage}
      />
    </main>
  )
}
