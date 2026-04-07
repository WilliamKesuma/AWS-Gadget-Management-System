import {
  createFileRoute,
  redirect,
  Outlet,
  Link,
  useNavigate,
  useMatchRoute,
} from '@tanstack/react-router'
import { z } from 'zod'
import { createColumnHelper, type ColumnDef } from '@tanstack/react-table'
import { lazy, Suspense, useState, useMemo, useCallback } from 'react'
import { format as formatISO } from 'date-fns'
import {
  type AssetItem,
  type AssetStatus,
  type UserRole,
} from '#/lib/models/types'
import { AssetStatusSchema } from '#/lib/models/types'
import { Badge } from '#/components/ui/badge'
import { cn, formatDate, formatNumber } from '#/lib/utils'
import { AssetStatusLabels } from '#/lib/models/labels'
import { AssetStatusVariants } from '#/lib/models/badge-variants'
import { useCursorPagination } from '#/hooks/use-cursor-pagination'
import { useAssets, type AssetFilters } from '#/hooks/use-assets'
import { useAllCategories, formatCategoryName } from '#/hooks/use-categories'
import { useDebounce } from '#/hooks/use-debounce'
import { useCurrentUserRole } from '#/hooks/use-current-user'
import { DataTable } from '#/components/general/DataTable'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import { Calendar } from '#/components/ui/calendar'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '#/components/ui/popover'
import { Tabs, TabsList, TabsTrigger } from '#/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '#/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '#/components/ui/dialog'
import {
  getBaseMeta,
  getPageMeta,
  getCanonicalLink,
  type SeoPageInput,
} from '../../lib/seo'
import {
  BoxIcon,
  CalendarIcon,
  CheckCircle2,
  Construction,
  Eye,
  MoreHorizontal,
  Settings2,
  User2Icon,
} from 'lucide-react'
import { toast } from 'sonner'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '#/components/ui/dropdown-menu'
import { hasRole, getAssetRowPermissions } from '#/lib/permissions'
import { getHandoverState, getVisibleActions } from '#/lib/asset-utils'
import { useHandoverForm, useSignedHandoverForm } from '#/hooks/use-assets'
import { StatCard } from '#/components/general/StatCard'
import { useAssetsPageStats } from '#/hooks/use-page-stats'

// Lazy-loaded dialogs
const AssignAssetModal = lazy(() =>
  import('#/components/assets/AssignAssetModal').then((m) => ({
    default: m.AssignAssetModal,
  })),
)
const CancelAssignmentDialog = lazy(() =>
  import('#/components/assets/CancelAssignmentDialog').then((m) => ({
    default: m.CancelAssignmentDialog,
  })),
)
const ManageCategoriesDialog = lazy(() =>
  import('#/components/assets/ManageCategoriesDialog').then((m) => ({
    default: m.ManageCategoriesDialog,
  })),
)

const ASSETS_SEO = {
  title: 'Asset Inventory',
  description:
    'Track, assign, and manage organization-wide hardware assets, monitor lifecycle status, and oversee equipment availability.',
  path: '/assets',
} satisfies SeoPageInput

const ASSETS_ALLOWED: UserRole[] = ['it-admin', 'management', 'employee']

const stockTabValues = [
  'all',
  'in_stock',
  'assigned',
  'in_maintenance',
] as const
const stockTabSchema = z.enum(stockTabValues).optional()
type StockTab = z.infer<typeof stockTabSchema>

const assetsSearchSchema = z.object({
  tab: z.string().optional(),
  status: AssetStatusSchema.optional(),
  category: z.string().optional(),
  brand: z.string().optional(),
  model_name: z.string().optional(),
  date_from: z.string().optional(),
  date_to: z.string().optional(),
})

export const Route = createFileRoute('/_authenticated/assets')({
  validateSearch: (raw: Record<string, unknown>) =>
    assetsSearchSchema.parse(raw),
  beforeLoad: ({ context }) => {
    if (!hasRole(context.userRole, ASSETS_ALLOWED)) {
      throw redirect({ to: '/unauthorized' })
    }
  },
  component: AssetsPage,
  head: () => ({
    meta: [
      ...getBaseMeta(),
      { name: 'robots', content: 'noindex, nofollow' },
      ...getPageMeta(ASSETS_SEO),
    ],
    links: [getCanonicalLink(ASSETS_SEO.path)],
  }),
})

const columnHelper = createColumnHelper<AssetItem>()
const PAGE_SIZE = 10

// ── Date picker (reused inside dialog) ────────────────────────────────────────

function DatePicker({
  value,
  onChange,
  placeholder,
}: {
  value: string | undefined
  onChange: (value: string | undefined) => void
  placeholder: string
}) {
  const parsed = value ? new Date(value) : undefined
  const isValidDate = parsed && !Number.isNaN(parsed.getTime())

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            'w-full justify-start text-left font-normal',
            !value && 'text-muted-foreground',
          )}
        >
          <CalendarIcon className="size-4" />
          {isValidDate ? formatDate(parsed) : placeholder}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={isValidDate ? parsed : undefined}
          onSelect={(date) =>
            onChange(date ? formatISO(date, 'yyyy-MM-dd') : undefined)
          }
          autoFocus
        />
      </PopoverContent>
    </Popover>
  )
}

// ── Filter dialog ─────────────────────────────────────────────────────────────

type DialogFilterState = {
  status: AssetStatus | 'all'
  category: string | 'all'
  brand: string
  date_from: string | undefined
  date_to: string | undefined
}

const EMPTY_DIALOG_FILTERS: DialogFilterState = {
  status: 'all',
  category: 'all',
  brand: '',
  date_from: undefined,
  date_to: undefined,
}

function AssetFilterDialog({
  open,
  onOpenChange,
  current,
  onApply,
  showCategoryFilter,
  categories,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  current: DialogFilterState
  onApply: (filters: DialogFilterState) => void
  showCategoryFilter: boolean
  categories: { category_id: string; category_name: string }[]
}) {
  const [draft, setDraft] = useState<DialogFilterState>(current)

  const handleOpenChange = (next: boolean) => {
    if (next) setDraft(current)
    onOpenChange(next)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Filter Assets</DialogTitle>
          <DialogDescription>
            Narrow down the asset list by status, brand, or creation date.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="filter-status">Status</Label>
            <Select
              value={draft.status}
              onValueChange={(v) =>
                setDraft((d) => ({ ...d, status: v as AssetStatus | 'all' }))
              }
            >
              <SelectTrigger id="filter-status" className="w-full">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                {(Object.keys(AssetStatusLabels) as AssetStatus[]).map((s) => (
                  <SelectItem key={s} value={s}>
                    {AssetStatusLabels[s]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {showCategoryFilter && (
            <div className="space-y-1.5">
              <Label htmlFor="filter-category">Category</Label>
              <Select
                value={draft.category}
                onValueChange={(v) =>
                  setDraft((d) => ({ ...d, category: v as string }))
                }
              >
                <SelectTrigger id="filter-category" className="w-full">
                  <SelectValue placeholder="All Categories" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  {categories.map((cat) => (
                    <SelectItem key={cat.category_id} value={cat.category_name}>
                      {formatCategoryName(cat.category_name)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
          <div className="space-y-1.5">
            <Label htmlFor="filter-brand">Brand</Label>
            <Input
              id="filter-brand"
              placeholder="e.g. Dell, Apple"
              value={draft.brand}
              onChange={(e) =>
                setDraft((d) => ({ ...d, brand: e.target.value }))
              }
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Created from</Label>
              <DatePicker
                value={draft.date_from}
                onChange={(v) => setDraft((d) => ({ ...d, date_from: v }))}
                placeholder="Start date"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Created to</Label>
              <DatePicker
                value={draft.date_to}
                onChange={(v) => setDraft((d) => ({ ...d, date_to: v }))}
                placeholder="End date"
              />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => setDraft(EMPTY_DIALOG_FILTERS)}
          >
            Reset
          </Button>
          <Button
            onClick={() => {
              onApply(draft)
              onOpenChange(false)
            }}
          >
            Apply Filters
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Row actions component ──────────────────────────────────────────────────────

function AssetRowActions({
  row,
  role,
}: {
  row: AssetItem
  role: UserRole | null
}) {
  const navigate = useNavigate()
  const [assignModalOpen, setAssignModalOpen] = useState(false)
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false)
  const handoverFormMutation = useHandoverForm(row.asset_id)
  const signedHandoverFormMutation = useSignedHandoverForm(row.asset_id)

  const handoverState = getHandoverState(row.status, row.assignment_date)
  const isAssignedUser = role === 'employee'
  const actions = role
    ? getVisibleActions(role, row.status, handoverState, isAssignedUser)
    : []

  // Management review action (existing behavior, moved into dropdown)
  const { canManagementReview: canReview } = getAssetRowPermissions({
    role,
    assetStatus: row.status,
  })

  const hasDropdownActions = actions.length > 0 || canReview

  const handleViewHandoverForm = () => {
    handoverFormMutation.mutate(undefined, {
      onSuccess: (data) => {
        window.open(data.presigned_url, '_blank')
      },
      onError: (err) => {
        toast.error((err as Error).message || 'Failed to load handover form.')
      },
    })
  }

  const handleViewSignedHandover = () => {
    signedHandoverFormMutation.mutate(undefined, {
      onSuccess: (data) => {
        window.open(data.presigned_url, '_blank')
      },
      onError: (err) => {
        toast.error(
          (err as Error).message || 'Failed to load signed handover form.',
        )
      },
    })
  }

  return (
    <>
      <div
        className="flex items-center justify-end gap-2"
        onClick={(e) => e.stopPropagation()}
      >
        <Button size="icon" variant="ghost" asChild>
          <Link
            to={'/assets/$asset_id' as any}
            params={{ asset_id: row.asset_id } as any}
            aria-label="View asset details"
          >
            <Eye className="size-4" />
          </Link>
        </Button>
        {hasDropdownActions && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <MoreHorizontal className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {actions.includes('assign') && (
                <DropdownMenuItem onClick={() => setAssignModalOpen(true)}>
                  Assign to Employee
                </DropdownMenuItem>
              )}
              {actions.includes('view-handover-form') && (
                <DropdownMenuItem
                  onClick={handleViewHandoverForm}
                  disabled={handoverFormMutation.isPending}
                >
                  View Handover Form
                </DropdownMenuItem>
              )}
              {actions.includes('view-signed-handover') && (
                <DropdownMenuItem
                  onClick={handleViewSignedHandover}
                  disabled={signedHandoverFormMutation.isPending}
                >
                  View Signed Handover Form
                </DropdownMenuItem>
              )}
              {actions.includes('cancel-assignment') && (
                <DropdownMenuItem
                  className="text-danger"
                  onClick={() => setCancelDialogOpen(true)}
                >
                  Cancel Assignment
                </DropdownMenuItem>
              )}
              {actions.includes('accept-asset') && (
                <DropdownMenuItem
                  onClick={() => {
                    void navigate({
                      to: '/assets/$asset_id' as any,
                      params: { asset_id: row.asset_id } as any,
                    })
                  }}
                >
                  Accept Asset
                </DropdownMenuItem>
              )}
              {canReview && (
                <DropdownMenuItem asChild>
                  <Link
                    to="/assets/$asset_id/approve"
                    params={{ asset_id: row.asset_id }}
                  >
                    Review
                  </Link>
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
      <Suspense fallback={null}>
        <AssignAssetModal
          open={assignModalOpen}
          onOpenChange={setAssignModalOpen}
          assetId={row.asset_id}
        />
        <CancelAssignmentDialog
          open={cancelDialogOpen}
          onOpenChange={setCancelDialogOpen}
          assetId={row.asset_id}
        />
      </Suspense>
    </>
  )
}

// ── Main page component ───────────────────────────────────────────────────────

function AssetsPage() {
  const role = useCurrentUserRole()
  const navigate = useNavigate()
  const matchRoute = useMatchRoute()
  const search = Route.useSearch()
  const [filterOpen, setFilterOpen] = useState(false)
  const [manageCategoriesOpen, setManageCategoriesOpen] = useState(false)

  const {
    currentCursor,
    goToNextPage,
    goToPreviousPage,
    resetPagination,
    canGoPrevious,
    pageSize,
  } = useCursorPagination(PAGE_SIZE)

  // ── Dynamic categories (for tabs + filter) ──────────────────────────────
  const { data: categoriesData } = useAllCategories()
  const categories = useMemo(
    () => categoriesData?.items ?? [],
    [categoriesData],
  )

  // ── Model name (outside dialog, debounced) ──────────────────────────────
  const modelNameRaw = search.model_name ?? ''
  const debouncedModelName = useDebounce(modelNameRaw, 400)

  const isItAdmin = hasRole(role, ['it-admin'])
  const isAdminOrManagement = hasRole(role, ['it-admin', 'management'])

  // ── Page stats (IT Admin only) ──────────────────────────────────────────
  const { data: pageStats, isLoading: pageStatsLoading } = useAssetsPageStats()

  // ── Build API filters from URL search params ───────────────────────────
  // For IT Admin, the stock tab maps to a status filter
  const stockTabStatus: AssetStatus | undefined = useMemo(() => {
    if (!isAdminOrManagement) return undefined
    const tab = search.tab
    if (tab === 'in_stock') return 'IN_STOCK'
    if (tab === 'assigned') return 'ASSIGNED'
    return undefined
  }, [isAdminOrManagement, search.tab])

  // "In Maintenance" tab is not yet supported by the backend
  const isMaintenanceTab =
    isAdminOrManagement && search.tab === 'in_maintenance'

  const filters: AssetFilters = useMemo(
    () => ({
      ...(stockTabStatus && { status: stockTabStatus }),
      ...(!stockTabStatus && search.status && { status: search.status }),
      ...(search.category && { category: search.category }),
      ...(search.brand && { brand: search.brand }),
      ...(debouncedModelName && { model_name: debouncedModelName }),
      ...(search.date_from && { date_from: search.date_from }),
      ...(search.date_to && { date_to: search.date_to }),
    }),
    [
      stockTabStatus,
      search.status,
      search.category,
      search.brand,
      debouncedModelName,
      search.date_from,
      search.date_to,
    ],
  )

  const { data, isLoading, error } = useAssets(
    filters,
    currentCursor,
    pageSize,
    !isMaintenanceTab,
  )

  // ── Navigation helpers ──────────────────────────────────────────────────
  const setSearch = useCallback(
    (updates: Partial<z.infer<typeof assetsSearchSchema>>) => {
      void navigate({
        to: '/assets',
        search: { ...search, ...updates },
        replace: true,
      })
    },
    [navigate, search],
  )

  const setSearchAndResetPage = useCallback(
    (updates: Partial<z.infer<typeof assetsSearchSchema>>) => {
      resetPagination()
      setSearch({ ...updates })
    },
    [setSearch, resetPagination],
  )

  // ── Dialog filter state (derived from URL) ──────────────────────────────
  const dialogFilters: DialogFilterState = useMemo(
    () => ({
      status: search.status ?? 'all',
      category: search.category ?? 'all',
      brand: search.brand ?? '',
      date_from: search.date_from,
      date_to: search.date_to,
    }),
    [
      search.status,
      search.category,
      search.brand,
      search.date_from,
      search.date_to,
    ],
  )

  const handleApplyDialogFilters = useCallback(
    (f: DialogFilterState) => {
      setSearchAndResetPage({
        status: f.status === 'all' ? undefined : f.status,
        category: f.category === 'all' ? undefined : f.category,
        brand: f.brand || undefined,
        date_from: f.date_from,
        date_to: f.date_to,
      })
    },
    [setSearchAndResetPage],
  )

  // For IT Admin and Management, category is a dialog filter; for employees it's a tab (not counted)
  const dialogFilterCount = [
    search.status,
    search.brand,
    search.date_from,
    search.date_to,
    ...(isAdminOrManagement ? [search.category] : []),
  ].filter(Boolean).length
  const hasAnyFilter =
    dialogFilterCount > 0 ||
    (!isAdminOrManagement && !!search.category) ||
    !!search.model_name ||
    (isAdminOrManagement && !!search.tab)

  const clearAllFilters = useCallback(() => {
    resetPagination()
    void navigate({ to: '/assets', search: {}, replace: true })
  }, [navigate, resetPagination])

  // ── Stock tab handler (IT Admin only) ───────────────────────────────────
  const handleStockTabChange = useCallback(
    (v: string) => {
      resetPagination()
      setSearchAndResetPage({
        tab: v === 'all' ? undefined : (v as StockTab),
        // Clear status filter when switching stock tabs since the tab drives status
        status: undefined,
      })
    },
    [setSearchAndResetPage, resetPagination],
  )

  // ── Columns ─────────────────────────────────────────────────────────────
  const columns = useMemo<ColumnDef<AssetItem, any>[]>(
    () => [
      columnHelper.accessor('asset_id', {
        header: 'ASSET ID',
        cell: (info) => (
          <span className="text-sm font-medium">{info.getValue()}</span>
        ),
      }),
      columnHelper.accessor('brand', {
        header: 'BRAND',
        cell: (info) => (
          <span className="text-sm font-medium">{info.getValue() ?? '—'}</span>
        ),
      }),
      columnHelper.accessor('model', {
        header: 'MODEL',
        cell: (info) => (
          <span className="text-sm font-medium">{info.getValue() ?? '—'}</span>
        ),
      }),
      columnHelper.accessor('serial_number', {
        header: 'SERIAL NUMBER',
        cell: (info) => (
          <span className="text-sm font-medium">{info.getValue() ?? '—'}</span>
        ),
      }),
      columnHelper.accessor('category', {
        header: 'CATEGORY',
        cell: (info) => {
          const cat = info.getValue() as string | undefined
          return (
            <span className="text-sm font-medium">
              {cat ? formatCategoryName(cat) : '—'}
            </span>
          )
        },
      }),
      columnHelper.accessor('status', {
        header: 'STATUS',
        cell: (info) => {
          const status = info.getValue() as AssetStatus
          return (
            <Badge variant={AssetStatusVariants[status] ?? 'info'}>
              {AssetStatusLabels[status]}
            </Badge>
          )
        },
      }),
      columnHelper.accessor('created_at', {
        header: 'CREATED',
        cell: (info) => (
          <span className="text-sm font-medium text-muted-foreground">
            {formatDate(info.getValue()) || '—'}
          </span>
        ),
      }),
      columnHelper.accessor('assignment_date', {
        header: 'ASSIGNMENT DATE',
        cell: (info) => (
          <span className="text-sm font-medium text-muted-foreground">
            {formatDate(info.getValue()) || '—'}
          </span>
        ),
      }),
      columnHelper.display({
        id: 'actions',
        header: '',
        cell: (info) => <AssetRowActions row={info.row.original} role={role} />,
      }),
    ],
    [role],
  )

  const tableData = useMemo(
    () => (isMaintenanceTab ? [] : (data?.items ?? [])),
    [data, isMaintenanceTab],
  )

  const assetIdMatch = matchRoute({ to: '/assets/$asset_id', fuzzy: true })
  const isNewRoute = matchRoute({ to: '/assets/new' })
  const isApproveRoute = matchRoute({
    to: '/assets/$asset_id/approve' as any,
    fuzzy: true,
  })
  const isChildRouteActive = assetIdMatch && !isNewRoute && !isApproveRoute

  if (isChildRouteActive) {
    return <Outlet />
  }

  return (
    <main className="page-base">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Asset Inventory</h1>
          <p className="page-subtitle">
            Manage and track organization-wide hardware assets.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {hasRole(role, ['management']) && (
            <Button
              variant="outline"
              size="lg"
              onClick={() => setManageCategoriesOpen(true)}
            >
              <Settings2 className="size-4 mr-2" />
              Manage Categories
            </Button>
          )}
          {hasRole(role, ['it-admin']) && (
            <Button size="lg" asChild>
              <Link to="/assets/new">Add New Asset</Link>
            </Button>
          )}
        </div>
      </div>

      {isItAdmin && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mt-4">
          <StatCard
            loading={pageStatsLoading}
            title="Total Assets"
            data={formatNumber(pageStats?.total_assets ?? 0)}
            Icon={BoxIcon}
          />
          <StatCard
            loading={pageStatsLoading}
            title="In Stock"
            data={formatNumber(pageStats?.in_stock ?? 0)}
            Icon={CheckCircle2}
          />
          <StatCard
            loading={pageStatsLoading}
            title="Assigned"
            data={formatNumber(pageStats?.assigned ?? 0)}
            Icon={User2Icon}
          />
          <StatCard
            loading={pageStatsLoading}
            title="In Maintenance"
            data={formatNumber(pageStats?.in_maintenance ?? 0)}
            Icon={Construction}
          />
        </div>
      )}

      {/* ── Tabs ──────────────────────────────────────────────────── */}
      {isAdminOrManagement ? (
        <Tabs
          value={search.tab ?? 'all'}
          onValueChange={handleStockTabChange}
          className="mt-4"
        >
          <TabsList variant="line">
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="in_stock">In Stock</TabsTrigger>
            <TabsTrigger value="assigned">Assigned</TabsTrigger>
            <TabsTrigger value="in_maintenance">In Maintenance</TabsTrigger>
          </TabsList>
        </Tabs>
      ) : (
        <Tabs
          value={search.category ?? 'all'}
          onValueChange={(v) =>
            setSearchAndResetPage({ category: v === 'all' ? undefined : v })
          }
          className="mt-4"
        >
          <TabsList variant="line">
            <TabsTrigger value="all">All</TabsTrigger>
            {categories.map((cat) => (
              <TabsTrigger key={cat.category_id} value={cat.category_name}>
                {formatCategoryName(cat.category_name)}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      )}

      {/* ── Toolbar ────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 mt-3">
        <Input
          placeholder="Search model..."
          aria-label="Search by model name"
          value={modelNameRaw}
          onChange={(e) =>
            setSearchAndResetPage({ model_name: e.target.value || undefined })
          }
          className="w-[220px]"
        />
        <Button variant="outline" size="sm" onClick={() => setFilterOpen(true)}>
          Filters
          {dialogFilterCount > 0 && (
            <Badge variant="default" size="sm" className="ml-1.5">
              {dialogFilterCount}
            </Badge>
          )}
        </Button>
        {hasAnyFilter && (
          <Button variant="ghost" size="sm" onClick={clearAllFilters}>
            Clear all
          </Button>
        )}
      </div>

      <DataTable
        columns={columns}
        data={tableData}
        entityName="assets"
        isLoading={isLoading}
        error={error ? (error as Error).message : undefined}
        pageSize={pageSize}
        hasNextPage={!isMaintenanceTab && (data?.has_next_page ?? false)}
        canGoPrevious={canGoPrevious}
        onNextPage={() => data?.next_cursor && goToNextPage(data.next_cursor)}
        onPreviousPage={goToPreviousPage}
      />

      <AssetFilterDialog
        open={filterOpen}
        onOpenChange={setFilterOpen}
        current={dialogFilters}
        onApply={handleApplyDialogFilters}
        showCategoryFilter={isAdminOrManagement}
        categories={categories}
      />

      <Suspense fallback={null}>
        <ManageCategoriesDialog
          open={manageCategoriesOpen}
          onOpenChange={setManageCategoriesOpen}
        />
      </Suspense>

      <Outlet />
    </main>
  )
}
