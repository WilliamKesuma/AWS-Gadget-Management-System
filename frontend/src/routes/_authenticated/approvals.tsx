import { lazy, Suspense, useState, useMemo, useCallback } from 'react'
import {
  createFileRoute,
  redirect,
  Link,
  useNavigate,
} from '@tanstack/react-router'
import { createColumnHelper, type ColumnDef } from '@tanstack/react-table'
import { z } from 'zod'
import { Eye } from 'lucide-react'
import {
  getBaseMeta,
  getPageMeta,
  getCanonicalLink,
  type SeoPageInput,
} from '../../lib/seo'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import { Switch } from '#/components/ui/switch'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '#/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '#/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '#/components/ui/select'
import { DataTable } from '#/components/general/DataTable'
import { SoftwareStatusBadge } from '#/components/software/SoftwareStatusBadge'
import { RiskLevelBadge } from '#/components/software/RiskLevelBadge'
import { useCursorPagination } from '#/hooks/use-cursor-pagination'
import { useAllSoftwareRequests } from '#/hooks/use-software-requests'
import { usePendingReplacements } from '#/hooks/use-issues'
import { useAssets } from '#/hooks/use-assets'
import { usePendingDisposals } from '#/hooks/use-disposals'
import { useCurrentUserRole } from '#/hooks/use-current-user'
import { hasRole } from '#/lib/permissions'
import { formatDate } from '#/lib/utils'
import {
  SoftwareStatusLabels,
  RiskLevelLabels,
  IssueStatusLabels,
  AssetStatusLabels,
  AssetConditionLabels,
} from '#/lib/models/labels'
import {
  IssueStatusVariants,
  AssetStatusVariants,
} from '#/lib/models/badge-variants'

// Lazy-loaded tab content
const DisposalsTabContent = lazy(() =>
  import('#/components/disposals/DisposalsTabContent').then((m) => ({
    default: m.DisposalsTabContent,
  })),
)

import {
  type UserRole,
  type SoftwareRequestListItem,
  type PendingReplacementListItem,
  type AssetItem,
  type AssetStatus,
  type AssetCondition,
  type SoftwareStatus,
  type IssueStatus,
  type DataAccessImpact,
  type ListSoftwareRequestsFilter,
  CATEGORY_VALUES,
  type TabDef,
  SoftwareStatusSchema,
  RiskLevelSchema,
  DataAccessImpactSchema,
  IssueStatusSchema,
  type RiskLevel,
} from '#/lib/models/types'

// ── SEO ───────────────────────────────────────────────────────────────────────

const APPROVALS_SEO = {
  title: 'Approvals',
  description:
    'Review and process pending approval requests for assets, software, replacements, and disposals.',
  path: '/approvals',
} satisfies SeoPageInput

// ── Tab definitions ───────────────────────────────────────────────────────────

const ALL_TABS: TabDef[] = [
  { value: 'all-requests', label: 'All Requests', roles: ['management'] },
  { value: 'asset-creation', label: 'Asset Creation', roles: ['management'] },
  {
    value: 'replacement',
    label: 'Replacement',
    roles: ['it-admin', 'management'],
  },
  { value: 'software', label: 'Software', roles: ['it-admin', 'management'] },
  { value: 'disposals', label: 'Disposals', roles: ['management'] },
]

// ── Route search params ───────────────────────────────────────────────────────

const approvalsSearchSchema = z.object({
  tab: z.enum(CATEGORY_VALUES).optional(),
  history: z.coerce.boolean().optional(),
  // Software filters
  status: SoftwareStatusSchema.optional(),
  risk_level: RiskLevelSchema.optional(),
  software_name: z.string().optional(),
  vendor: z.string().optional(),
  license_validity_period: z.string().optional(),
  data_access_impact: DataAccessImpactSchema.optional(),
  // Replacement filters
  replacement_status: IssueStatusSchema.optional(),
  reported_by: z.string().optional(),
})

// ── Route config ──────────────────────────────────────────────────────────────

const APPROVALS_ALLOWED: UserRole[] = ['it-admin', 'management']

export const Route = createFileRoute('/_authenticated/approvals')({
  beforeLoad: ({ context }) => {
    if (!hasRole(context.userRole, APPROVALS_ALLOWED)) {
      throw redirect({ to: '/unauthorized' })
    }
  },
  validateSearch: (raw: Record<string, unknown>) =>
    approvalsSearchSchema.parse(raw),
  component: ApprovalsPage,
  head: () => ({
    meta: [
      ...getBaseMeta(),
      { name: 'robots', content: 'noindex, nofollow' },
      ...getPageMeta(APPROVALS_SEO),
    ],
    links: [getCanonicalLink(APPROVALS_SEO.path)],
  }),
})

// ── Column helpers + constants ────────────────────────────────────────────────

const softwareColumnHelper = createColumnHelper<SoftwareRequestListItem>()
const replacementColumnHelper = createColumnHelper<PendingReplacementListItem>()
const assetColumnHelper = createColumnHelper<AssetItem>()
const PAGE_SIZE = 10

// ── Software filter dialog state ──────────────────────────────────────────────

type SoftwareDialogFilterState = {
  status: SoftwareStatus | 'all'
  risk_level: RiskLevel | 'all'
  software_name: string
  vendor: string
  license_validity_period: string
  data_access_impact: DataAccessImpact | 'all'
}

const EMPTY_SOFTWARE_FILTERS: SoftwareDialogFilterState = {
  status: 'all',
  risk_level: 'all',
  software_name: '',
  vendor: '',
  license_validity_period: '',
  data_access_impact: 'all',
}

// ── Replacement filter dialog state ───────────────────────────────────────────

type ReplacementDialogFilterState = {
  replacement_status: IssueStatus | 'all'
  reported_by: string
}

const EMPTY_REPLACEMENT_FILTERS: ReplacementDialogFilterState = {
  replacement_status: 'all',
  reported_by: '',
}

// ── Software Request Filter Dialog ────────────────────────────────────────────

function SoftwareRequestFilterDialog({
  open,
  onOpenChange,
  current,
  onApply,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  current: SoftwareDialogFilterState
  onApply: (filters: SoftwareDialogFilterState) => void
}) {
  const [draft, setDraft] = useState<SoftwareDialogFilterState>(current)

  const handleOpenChange = (next: boolean) => {
    if (next) setDraft(current)
    onOpenChange(next)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Filter Software Requests</DialogTitle>
          <DialogDescription>
            Narrow down the software request list by status, risk level, or
            other criteria.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 overflow-y-auto -mx-1 px-1">
          <div className="space-y-1.5">
            <Label htmlFor="filter-status">Status</Label>
            <Select
              value={draft.status}
              onValueChange={(v) =>
                setDraft((d) => ({ ...d, status: v as SoftwareStatus | 'all' }))
              }
            >
              <SelectTrigger id="filter-status" className="w-full">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                {(Object.keys(SoftwareStatusLabels) as SoftwareStatus[]).map(
                  (s) => (
                    <SelectItem key={s} value={s}>
                      {SoftwareStatusLabels[s]}
                    </SelectItem>
                  ),
                )}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="filter-risk-level">Risk Level</Label>
            <Select
              value={draft.risk_level}
              onValueChange={(v) =>
                setDraft((d) => ({
                  ...d,
                  risk_level: v as 'LOW' | 'MEDIUM' | 'HIGH' | 'all',
                }))
              }
            >
              <SelectTrigger id="filter-risk-level" className="w-full">
                <SelectValue placeholder="All" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                {(
                  Object.keys(RiskLevelLabels) as ('LOW' | 'MEDIUM' | 'HIGH')[]
                ).map((r) => (
                  <SelectItem key={r} value={r}>
                    {RiskLevelLabels[r]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="filter-software-name">Software Name</Label>
            <Input
              id="filter-software-name"
              placeholder="e.g. Visual Studio Code"
              value={draft.software_name}
              onChange={(e) =>
                setDraft((d) => ({ ...d, software_name: e.target.value }))
              }
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="filter-vendor">Vendor</Label>
            <Input
              id="filter-vendor"
              placeholder="e.g. Microsoft"
              value={draft.vendor}
              onChange={(e) =>
                setDraft((d) => ({ ...d, vendor: e.target.value }))
              }
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="filter-license-validity">
              License Validity Period
            </Label>
            <Input
              id="filter-license-validity"
              placeholder="e.g. 1 year"
              value={draft.license_validity_period}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  license_validity_period: e.target.value,
                }))
              }
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="filter-data-access-impact">
              Data Access Impact
            </Label>
            <Select
              value={draft.data_access_impact}
              onValueChange={(v) =>
                setDraft((d) => ({
                  ...d,
                  data_access_impact: v as DataAccessImpact | 'all',
                }))
              }
            >
              <SelectTrigger id="filter-data-access-impact" className="w-full">
                <SelectValue placeholder="All" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                {(
                  Object.keys(RiskLevelLabels) as ('LOW' | 'MEDIUM' | 'HIGH')[]
                ).map((r) => (
                  <SelectItem key={r} value={r}>
                    {RiskLevelLabels[r]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => setDraft(EMPTY_SOFTWARE_FILTERS)}
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

// ── Replacement Filter Dialog ─────────────────────────────────────────────────

function ReplacementFilterDialog({
  open,
  onOpenChange,
  current,
  onApply,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  current: ReplacementDialogFilterState
  onApply: (filters: ReplacementDialogFilterState) => void
}) {
  const [draft, setDraft] = useState<ReplacementDialogFilterState>(current)

  const handleOpenChange = (next: boolean) => {
    if (next) setDraft(current)
    onOpenChange(next)
  }

  // Only replacement-relevant statuses
  const replacementStatuses: IssueStatus[] = [
    'REPLACEMENT_REQUIRED',
    'REPLACEMENT_APPROVED',
    'REPLACEMENT_REJECTED',
  ]

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Filter Replacement Requests</DialogTitle>
          <DialogDescription>
            Narrow down the replacement request list by status or reporter.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 overflow-y-auto -mx-1 px-1">
          <div className="space-y-1.5">
            <Label htmlFor="filter-replacement-status">Status</Label>
            <Select
              value={draft.replacement_status}
              onValueChange={(v) =>
                setDraft((d) => ({
                  ...d,
                  replacement_status: v as IssueStatus | 'all',
                }))
              }
            >
              <SelectTrigger id="filter-replacement-status" className="w-full">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                {replacementStatuses.map((s) => (
                  <SelectItem key={s} value={s}>
                    {IssueStatusLabels[s]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="filter-reported-by">Reported By</Label>
            <Input
              id="filter-reported-by"
              placeholder="e.g. John Doe"
              value={draft.reported_by}
              onChange={(e) =>
                setDraft((d) => ({ ...d, reported_by: e.target.value }))
              }
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => setDraft(EMPTY_REPLACEMENT_FILTERS)}
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

// ── Asset Creation Tab Content ────────────────────────────────────────────────

const assetCreationColumns: ColumnDef<AssetItem, any>[] = [
  assetColumnHelper.accessor('asset_id', {
    header: 'ASSET ID',
    cell: (info) => (
      <Link
        to="/assets/$asset_id"
        params={{ asset_id: info.getValue() }}
        className="text-sm font-medium text-info hover:underline"
      >
        {info.getValue()}
      </Link>
    ),
  }),
  assetColumnHelper.accessor('brand', {
    header: 'BRAND',
    cell: (info) => (
      <span className="text-sm font-medium">{info.getValue() ?? '—'}</span>
    ),
  }),
  assetColumnHelper.accessor('model', {
    header: 'MODEL',
    cell: (info) => (
      <span className="text-sm font-medium">{info.getValue() ?? '—'}</span>
    ),
  }),
  assetColumnHelper.accessor('category', {
    header: 'CATEGORY',
    cell: (info) => <span className="text-sm">{info.getValue() ?? '—'}</span>,
  }),
  assetColumnHelper.accessor('condition', {
    header: 'CONDITION',
    cell: (info) => {
      const val = info.getValue() as AssetCondition | undefined
      return (
        <span className="text-sm">{val ? AssetConditionLabels[val] : '—'}</span>
      )
    },
  }),
  assetColumnHelper.accessor('status', {
    header: 'STATUS',
    cell: (info) => {
      const val = info.getValue() as AssetStatus
      return (
        <Badge
          variant={AssetStatusVariants[val] ?? 'warning'}
          className="text-xs"
        >
          {AssetStatusLabels[val]}
        </Badge>
      )
    },
  }),
  assetColumnHelper.accessor('created_at', {
    header: 'CREATED AT',
    cell: (info) => (
      <span className="text-sm text-muted-foreground">
        {formatDate(info.getValue()) || '—'}
      </span>
    ),
  }),
  assetColumnHelper.display({
    id: 'actions',
    header: '',
    cell: (info) => (
      <div className="flex items-center justify-end">
        <Button size="icon" variant="ghost" asChild>
          <Link
            to={'/assets/$asset_id/approve' as any}
            params={{ asset_id: info.row.original.asset_id } as any}
            aria-label="View details"
          >
            <Eye className="size-4" />
          </Link>
        </Button>
      </div>
    ),
  }),
]

function AssetCreationTabContent() {
  const {
    currentCursor,
    goToNextPage,
    goToPreviousPage,
    canGoPrevious,
    pageSize,
  } = useCursorPagination(PAGE_SIZE)

  const { data, isLoading, error } = useAssets(
    { status: 'ASSET_PENDING_APPROVAL' },
    currentCursor,
    pageSize,
  )

  const tableData = useMemo(() => data?.items ?? [], [data])

  return (
    <DataTable
      columns={assetCreationColumns}
      data={tableData}
      entityName="asset creation requests"
      isLoading={isLoading}
      error={error ? (error as Error).message : undefined}
      pageSize={pageSize}
      hasNextPage={data?.has_next_page ?? false}
      canGoPrevious={canGoPrevious}
      onNextPage={() => data?.next_cursor && goToNextPage(data.next_cursor)}
      onPreviousPage={goToPreviousPage}
    />
  )
}

// ── Replacement Tab Content ───────────────────────────────────────────────────

function ReplacementTabContent({ history }: { history: boolean }) {
  const navigate = useNavigate()
  const search = Route.useSearch()
  const [filterOpen, setFilterOpen] = useState(false)
  const {
    currentCursor,
    goToNextPage,
    goToPreviousPage,
    resetPagination,
    canGoPrevious,
    pageSize,
  } = useCursorPagination(PAGE_SIZE)

  const onSearchChange = useCallback(
    (updates: Partial<z.infer<typeof approvalsSearchSchema>>) => {
      resetPagination()
      void navigate({
        to: '.',
        search: (prev: Record<string, unknown>) => ({ ...prev, ...updates }) as any,
        replace: true,
      })
    },
    [navigate, resetPagination],
  )

  const { data, isLoading, error } = usePendingReplacements(
    currentCursor,
    pageSize,
    history,
  )

  const dialogFilters: ReplacementDialogFilterState = useMemo(
    () => ({
      replacement_status: search.replacement_status ?? 'all',
      reported_by: search.reported_by ?? '',
    }),
    [search.replacement_status, search.reported_by],
  )

  const handleApplyDialogFilters = useCallback(
    (f: ReplacementDialogFilterState) => {
      onSearchChange({
        replacement_status:
          f.replacement_status === 'all' ? undefined : f.replacement_status,
        reported_by: f.reported_by || undefined,
      })
    },
    [onSearchChange],
  )

  const dialogFilterCount = [
    search.replacement_status,
    search.reported_by,
  ].filter(Boolean).length
  const hasAnyFilter = dialogFilterCount > 0

  const clearAllFilters = useCallback(() => {
    onSearchChange({
      replacement_status: undefined,
      reported_by: undefined,
    })
  }, [onSearchChange])

  // Client-side filter on the fetched page (API doesn't support these params)
  const tableData = useMemo(() => {
    let items = data?.items ?? []
    if (search.replacement_status) {
      items = items.filter((i) => i.status === search.replacement_status)
    }
    if (search.reported_by) {
      const q = search.reported_by.toLowerCase()
      items = items.filter((i) => i.reported_by.toLowerCase().includes(q))
    }
    return items
  }, [data, search.replacement_status, search.reported_by])

  const columns = useMemo<ColumnDef<PendingReplacementListItem, any>[]>(
    () => [
      replacementColumnHelper.accessor('issue_id', {
        header: 'ISSUE ID',
        cell: (info) => (
          <Link
            to="/assets/$asset_id/issues/$issue_id"
            params={{
              asset_id: info.row.original.asset_id,
              issue_id: info.getValue(),
            }}
            className="text-sm font-medium text-info hover:underline"
          >
            {info.getValue()}
          </Link>
        ),
      }),
      replacementColumnHelper.accessor('asset_id', {
        header: 'ASSET ID',
        cell: (info) => (
          <Link
            to="/assets/$asset_id"
            params={{ asset_id: info.getValue() }}
            className="text-sm font-medium text-info hover:underline"
          >
            {info.getValue()}
          </Link>
        ),
      }),
      replacementColumnHelper.accessor('issue_description', {
        header: 'ISSUE DESCRIPTION',
        cell: (info) => (
          <span
            className="text-sm truncate max-w-[200px] block"
            title={info.getValue()}
          >
            {info.getValue()}
          </span>
        ),
      }),
      replacementColumnHelper.accessor('replacement_justification', {
        header: 'JUSTIFICATION',
        cell: (info) => (
          <span
            className="text-sm truncate max-w-[200px] block"
            title={info.getValue()}
          >
            {info.getValue()}
          </span>
        ),
      }),
      replacementColumnHelper.accessor('reported_by', {
        header: 'REPORTED BY',
        cell: (info) => (
          <span className="text-sm font-medium">{info.getValue()}</span>
        ),
      }),
      replacementColumnHelper.accessor('status', {
        header: 'STATUS',
        cell: (info) => (
          <Badge
            variant={
              IssueStatusVariants[info.getValue() as IssueStatus] ?? 'warning'
            }
            className="text-xs"
          >
            {IssueStatusLabels[info.getValue() as IssueStatus]}
          </Badge>
        ),
      }),
      replacementColumnHelper.accessor('created_at', {
        header: 'CREATED AT',
        cell: (info) => (
          <span className="text-sm text-muted-foreground">
            {formatDate(info.getValue()) || '—'}
          </span>
        ),
      }),
      replacementColumnHelper.display({
        id: 'actions',
        header: '',
        cell: (info) => (
          <div className="flex items-center justify-end">
            <Button size="icon" variant="ghost" asChild>
              <Link
                to="/assets/$asset_id/issues/$issue_id"
                params={{
                  asset_id: info.row.original.asset_id,
                  issue_id: info.row.original.issue_id,
                }}
                aria-label="View details"
              >
                <Eye className="size-4" />
              </Link>
            </Button>
          </div>
        ),
      }),
    ],
    [],
  )

  return (
    <>
      <div className="flex items-center gap-3">
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
        entityName="replacement requests"
        isLoading={isLoading}
        error={error ? (error as Error).message : undefined}
        pageSize={pageSize}
        hasNextPage={data?.has_next_page ?? false}
        canGoPrevious={canGoPrevious}
        onNextPage={() => data?.next_cursor && goToNextPage(data.next_cursor)}
        onPreviousPage={goToPreviousPage}
      />

      <ReplacementFilterDialog
        open={filterOpen}
        onOpenChange={setFilterOpen}
        current={dialogFilters}
        onApply={handleApplyDialogFilters}
      />
    </>
  )
}

// ── Software Requests Tab Content ─────────────────────────────────────────────

function SoftwareRequestsTabContent() {
  const navigate = useNavigate()
  const search = Route.useSearch()
  const [filterOpen, setFilterOpen] = useState(false)
  const {
    currentCursor,
    goToNextPage,
    goToPreviousPage,
    resetPagination,
    canGoPrevious,
    pageSize,
  } = useCursorPagination(PAGE_SIZE)

  const onSearchChange = useCallback(
    (updates: Partial<z.infer<typeof approvalsSearchSchema>>) => {
      resetPagination()
      void navigate({
        to: '.',
        search: (prev: Record<string, unknown>) => ({ ...prev, ...updates }) as any,
        replace: true,
      })
    },
    [navigate, resetPagination],
  )

  const filters: ListSoftwareRequestsFilter = useMemo(
    () => ({
      ...(search.status && { status: search.status }),
      ...(search.risk_level && { risk_level: search.risk_level }),
      ...(search.software_name && { software_name: search.software_name }),
      ...(search.vendor && { vendor: search.vendor }),
      ...(search.license_validity_period && {
        license_validity_period: search.license_validity_period,
      }),
      ...(search.data_access_impact && {
        data_access_impact: search.data_access_impact,
      }),
    }),
    [
      search.status,
      search.risk_level,
      search.software_name,
      search.vendor,
      search.license_validity_period,
      search.data_access_impact,
    ],
  )

  const { data, isLoading, error } = useAllSoftwareRequests(
    filters,
    currentCursor,
    pageSize,
  )

  const setSearchAndResetPage = useCallback(
    (updates: Partial<z.infer<typeof approvalsSearchSchema>>) => {
      onSearchChange({ ...updates })
    },
    [onSearchChange],
  )

  const dialogFilters: SoftwareDialogFilterState = useMemo(
    () => ({
      status: search.status ?? 'all',
      risk_level: search.risk_level ?? 'all',
      software_name: search.software_name ?? '',
      vendor: search.vendor ?? '',
      license_validity_period: search.license_validity_period ?? '',
      data_access_impact: search.data_access_impact ?? 'all',
    }),
    [
      search.status,
      search.risk_level,
      search.software_name,
      search.vendor,
      search.license_validity_period,
      search.data_access_impact,
    ],
  )

  const handleApplyDialogFilters = useCallback(
    (f: SoftwareDialogFilterState) => {
      setSearchAndResetPage({
        status: f.status === 'all' ? undefined : f.status,
        risk_level: f.risk_level === 'all' ? undefined : f.risk_level,
        software_name: f.software_name || undefined,
        vendor: f.vendor || undefined,
        license_validity_period: f.license_validity_period || undefined,
        data_access_impact:
          f.data_access_impact === 'all' ? undefined : f.data_access_impact,
      })
    },
    [setSearchAndResetPage],
  )

  const dialogFilterCount = [
    search.status,
    search.risk_level,
    search.software_name,
    search.vendor,
    search.license_validity_period,
    search.data_access_impact,
  ].filter(Boolean).length

  const hasAnyFilter = dialogFilterCount > 0

  const clearAllFilters = useCallback(() => {
    onSearchChange({
      status: undefined,
      risk_level: undefined,
      software_name: undefined,
      vendor: undefined,
      license_validity_period: undefined,
      data_access_impact: undefined,
    })
  }, [onSearchChange])

  const columns = useMemo<ColumnDef<SoftwareRequestListItem, any>[]>(
    () => [
      softwareColumnHelper.accessor('software_request_id', {
        header: 'REQUEST ID',
        cell: (info) => (
          <Link
            to={
              '/assets/$asset_id/software-requests/$software_request_id' as any
            }
            params={
              {
                asset_id: info.row.original.asset_id,
                software_request_id: info.getValue(),
              } as any
            }
            className="text-sm font-medium text-info hover:underline"
          >
            {info.getValue()}
          </Link>
        ),
      }),
      softwareColumnHelper.accessor('asset_id', {
        header: 'ASSET ID',
        cell: (info) => (
          <Link
            to="/assets/$asset_id"
            params={{ asset_id: info.getValue() }}
            className="text-sm font-medium text-info hover:underline"
          >
            {info.getValue()}
          </Link>
        ),
      }),
      softwareColumnHelper.accessor('software_name', {
        header: 'SOFTWARE NAME',
        cell: (info) => (
          <span className="text-sm font-medium">{info.getValue()}</span>
        ),
      }),
      softwareColumnHelper.accessor('version', {
        header: 'VERSION',
        cell: (info) => (
          <span className="text-sm font-medium">{info.getValue()}</span>
        ),
      }),
      softwareColumnHelper.accessor('vendor', {
        header: 'VENDOR',
        cell: (info) => (
          <span className="text-sm font-medium">{info.getValue()}</span>
        ),
      }),
      softwareColumnHelper.accessor('status', {
        header: 'STATUS',
        cell: (info) => <SoftwareStatusBadge status={info.getValue()} />,
      }),
      softwareColumnHelper.accessor('risk_level', {
        header: 'RISK LEVEL',
        cell: (info) => <RiskLevelBadge value={info.getValue() ?? null} />,
      }),
      softwareColumnHelper.accessor('requested_by', {
        header: 'REQUESTED BY',
        cell: (info) => (
          <span className="text-sm font-medium">{info.getValue()}</span>
        ),
      }),
      softwareColumnHelper.accessor('created_at', {
        header: 'CREATED AT',
        cell: (info) => (
          <span className="text-sm font-medium text-muted-foreground">
            {formatDate(info.getValue()) || '—'}
          </span>
        ),
      }),
      softwareColumnHelper.display({
        id: 'actions',
        header: '',
        cell: (info) => (
          <div className="flex items-center justify-end">
            <Button size="icon" variant="ghost" asChild>
              <Link
                to={
                  '/assets/$asset_id/software-requests/$software_request_id' as any
                }
                params={
                  {
                    asset_id: info.row.original.asset_id,
                    software_request_id: info.row.original.software_request_id,
                  } as any
                }
                aria-label="View details"
              >
                <Eye className="size-4" />
              </Link>
            </Button>
          </div>
        ),
      }),
    ],
    [],
  )

  const tableData = useMemo(() => data?.items ?? [], [data])

  return (
    <>
      <div className="flex items-center gap-3">
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
        entityName="software requests"
        isLoading={isLoading}
        error={error ? (error as Error).message : undefined}
        pageSize={pageSize}
        hasNextPage={data?.has_next_page ?? false}
        canGoPrevious={canGoPrevious}
        onNextPage={() => data?.next_cursor && goToNextPage(data.next_cursor)}
        onPreviousPage={goToPreviousPage}
      />

      <SoftwareRequestFilterDialog
        open={filterOpen}
        onOpenChange={setFilterOpen}
        current={dialogFilters}
        onApply={handleApplyDialogFilters}
      />
    </>
  )
}

// ── All Requests Tab Content ──────────────────────────────────────────────────

type UnifiedApprovalRow = {
  id: string
  type: 'Asset Creation' | 'Replacement' | 'Software' | 'Disposal'
  asset_id: string
  description: string
  requested_by: string
  created_at: string
  link_to: string
  link_params: Record<string, string>
}

const unifiedColumnHelper = createColumnHelper<UnifiedApprovalRow>()

const unifiedColumns: ColumnDef<UnifiedApprovalRow, any>[] = [
  unifiedColumnHelper.accessor('type', {
    header: 'TYPE',
    cell: (info) => (
      <Badge variant="secondary" className="text-xs">
        {info.getValue()}
      </Badge>
    ),
  }),
  unifiedColumnHelper.accessor('asset_id', {
    header: 'ASSET ID',
    cell: (info) => (
      <Link
        to="/assets/$asset_id"
        params={{ asset_id: info.getValue() }}
        className="text-sm font-medium text-info hover:underline"
      >
        {info.getValue()}
      </Link>
    ),
  }),
  unifiedColumnHelper.accessor('description', {
    header: 'DESCRIPTION',
    cell: (info) => (
      <span
        className="text-sm truncate max-w-[250px] block"
        title={info.getValue()}
      >
        {info.getValue()}
      </span>
    ),
  }),
  unifiedColumnHelper.accessor('requested_by', {
    header: 'REQUESTED BY',
    cell: (info) => (
      <span className="text-sm font-medium">{info.getValue()}</span>
    ),
  }),
  unifiedColumnHelper.accessor('created_at', {
    header: 'CREATED AT',
    cell: (info) => (
      <span className="text-sm text-muted-foreground">
        {formatDate(info.getValue()) || '—'}
      </span>
    ),
  }),
  unifiedColumnHelper.display({
    id: 'actions',
    header: '',
    cell: (info) => (
      <div className="flex items-center justify-end">
        <Button size="icon" variant="ghost" asChild>
          <Link
            to={info.row.original.link_to as any}
            params={info.row.original.link_params as any}
            aria-label="View details"
          >
            <Eye className="size-4" />
          </Link>
        </Button>
      </div>
    ),
  }),
]

function AllRequestsTabContent() {
  const assets = useAssets({ status: 'ASSET_PENDING_APPROVAL' }, undefined, 100)
  const replacements = usePendingReplacements(undefined, 100)
  const software = useAllSoftwareRequests({}, undefined, 100)
  const disposals = usePendingDisposals(undefined, 100)

  const isLoading =
    assets.isLoading ||
    replacements.isLoading ||
    software.isLoading ||
    disposals.isLoading
  const error =
    assets.error || replacements.error || software.error || disposals.error

  const allRows = useMemo<UnifiedApprovalRow[]>(() => {
    const rows: UnifiedApprovalRow[] = []

    for (const a of assets.data?.items ?? []) {
      rows.push({
        id: `asset-${a.asset_id}`,
        type: 'Asset Creation',
        asset_id: a.asset_id,
        description:
          [a.brand, a.model].filter(Boolean).join(' ') || 'New asset',
        requested_by: '—',
        created_at: a.created_at ?? '',
        link_to: '/assets/$asset_id/approve',
        link_params: { asset_id: a.asset_id },
      })
    }

    for (const r of replacements.data?.items ?? []) {
      rows.push({
        id: `replacement-${r.issue_id}`,
        type: 'Replacement',
        asset_id: r.asset_id,
        description: r.issue_description,
        requested_by: r.reported_by,
        created_at: r.created_at,
        link_to: '/assets/$asset_id/issues/$issue_id',
        link_params: { asset_id: r.asset_id, issue_id: r.issue_id },
      })
    }

    for (const s of software.data?.items ?? []) {
      rows.push({
        id: `software-${s.software_request_id}`,
        type: 'Software',
        asset_id: s.asset_id,
        description: `${s.software_name} ${s.version}`,
        requested_by: s.requested_by,
        created_at: s.created_at,
        link_to: '/assets/$asset_id/software-requests/$software_request_id',
        link_params: {
          asset_id: s.asset_id,
          software_request_id: s.software_request_id,
        },
      })
    }

    for (const d of disposals.data?.items ?? []) {
      rows.push({
        id: `disposal-${d.disposal_id}`,
        type: 'Disposal',
        asset_id: d.asset_id,
        description: d.disposal_reason,
        requested_by: d.initiated_by,
        created_at: d.initiated_at,
        link_to: '/assets/$asset_id/disposals/$disposal_id',
        link_params: { asset_id: d.asset_id, disposal_id: d.disposal_id },
      })
    }

    // Sort by created_at descending
    rows.sort((a, b) => (b.created_at > a.created_at ? 1 : -1))
    return rows
  }, [assets.data, replacements.data, software.data, disposals.data])

  return (
    <DataTable
      columns={unifiedColumns}
      data={allRows}
      entityName="approval requests"
      isLoading={isLoading}
      error={error ? (error as Error).message : undefined}
      pageSize={allRows.length || PAGE_SIZE}
    />
  )
}

// ── Main page component ───────────────────────────────────────────────────────

function ApprovalsPage() {
  const navigate = useNavigate()
  const search = Route.useSearch()
  const role = useCurrentUserRole()

  const showHistory = search.history ?? false

  const visibleTabs = useMemo(
    () => ALL_TABS.filter((t) => role && t.roles.includes(role)),
    [role],
  )

  const defaultTab = visibleTabs[0]?.value ?? 'replacement'
  const activeTab =
    search.tab && visibleTabs.some((t) => t.value === search.tab)
      ? search.tab
      : defaultTab

  const handleTabChange = useCallback(
    (value: string) => {
      void navigate({
        to: '.',
        search: {
          tab: value as (typeof CATEGORY_VALUES)[number],
          history: search.history,
        } as any,
        replace: true,
      })
    },
    [navigate, search.history],
  )

  const handleHistoryToggle = useCallback(
    (checked: boolean) => {
      void navigate({
        to: '.',
        search: (prev: Record<string, unknown>) =>
          ({ ...prev, history: checked || undefined }) as any,
        replace: true,
      })
    },
    [navigate],
  )

  return (
    <main className="page-base">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="page-title">Approvals</h1>
          <p className="page-subtitle">
            Centralized dashboard for reviewing and processing pending approval
            requests.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Label
            htmlFor="approvals-history-toggle"
            className="text-sm text-muted-foreground"
          >
            Show History
          </Label>
          <Switch
            id="approvals-history-toggle"
            checked={showHistory}
            onCheckedChange={handleHistoryToggle}
          />
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={handleTabChange} className="mt-4">
        <TabsList variant="line">
          {visibleTabs.map((t) => (
            <TabsTrigger key={t.value} value={t.value}>
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="all-requests" className="space-y-4 mt-4">
          <AllRequestsTabContent />
        </TabsContent>

        <TabsContent value="asset-creation" className="space-y-4 mt-4">
          <AssetCreationTabContent />
        </TabsContent>

        <TabsContent value="replacement" className="space-y-4 mt-4">
          <ReplacementTabContent history={showHistory} />
        </TabsContent>

        <TabsContent value="software" className="space-y-4 mt-4">
          <SoftwareRequestsTabContent />
        </TabsContent>

        <TabsContent value="disposals" className="space-y-4 mt-4">
          <Suspense fallback={<div className="py-12 text-center text-sm text-muted-foreground">Loading disposals...</div>}>
            <DisposalsTabContent
              history={showHistory}
            />
          </Suspense>
        </TabsContent>
      </Tabs>
    </main>
  )
}
