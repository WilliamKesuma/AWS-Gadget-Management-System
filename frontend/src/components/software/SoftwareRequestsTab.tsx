import { useState, useMemo, useCallback, useEffect } from 'react'
import { createColumnHelper, type ColumnDef } from '@tanstack/react-table'
import { Link } from '@tanstack/react-router'
import { Eye } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
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
import { SoftwareStatusBadge } from './SoftwareStatusBadge'
import { RiskLevelBadge } from './RiskLevelBadge'
import { useSoftwareRequests } from '#/hooks/use-software-requests'
import { useCursorPagination } from '#/hooks/use-cursor-pagination'
import { formatDate } from '#/lib/utils'
import { SoftwareStatusLabels, RiskLevelLabels } from '#/lib/models/labels'
import type {
  SoftwareRequestListItem,
  SoftwareStatus,
  DataAccessImpact,
  ListSoftwareRequestsFilter,
} from '#/lib/models/types'

// ── Types ─────────────────────────────────────────────────────────────────────

export type SoftwareRequestsTabProps = {
  assetId: string
  search: {
    status?: SoftwareStatus
    risk_level?: 'LOW' | 'MEDIUM' | 'HIGH'
    software_name?: string
    vendor?: string
    license_validity_period?: string
    data_access_impact?: DataAccessImpact
  }
  onSearchChange: (updates: Partial<SoftwareRequestsTabProps['search']>) => void
}

// ── Column helper + constants ─────────────────────────────────────────────────

const columnHelper = createColumnHelper<SoftwareRequestListItem>()
const PAGE_SIZE = 10

// ── Filter dialog state ───────────────────────────────────────────────────────

type DialogFilterState = {
  status: SoftwareStatus | 'all'
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'all'
  software_name: string
  vendor: string
  license_validity_period: string
  data_access_impact: DataAccessImpact | 'all'
}

const EMPTY_DIALOG_FILTERS: DialogFilterState = {
  status: 'all',
  risk_level: 'all',
  software_name: '',
  vendor: '',
  license_validity_period: '',
  data_access_impact: 'all',
}

// ── Filter Dialog ─────────────────────────────────────────────────────────────

function SoftwareRequestFilterDialog({
  open,
  onOpenChange,
  current,
  onApply,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  current: DialogFilterState
  onApply: (filters: DialogFilterState) => void
}) {
  const [draft, setDraft] = useState<DialogFilterState>(current)

  const handleOpenChange = (next: boolean) => {
    if (next) setDraft(current)
    onOpenChange(next)
  }

  const handleReset = () => setDraft(EMPTY_DIALOG_FILTERS)

  const handleApply = () => {
    onApply(draft)
    onOpenChange(false)
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

        <div className="space-y-4 -mx-1 px-1">
          {/* Status */}
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

          {/* Risk Level */}
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

          {/* Software Name */}
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

          {/* Vendor */}
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

          {/* License Validity Period */}
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

          {/* Data Access Impact */}
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
          <Button variant="ghost" onClick={handleReset}>
            Reset
          </Button>
          <Button onClick={handleApply}>Apply Filters</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function SoftwareRequestsTab({
  assetId,
  search,
  onSearchChange,
}: SoftwareRequestsTabProps) {
  const [filterOpen, setFilterOpen] = useState(false)
  const {
    currentCursor,
    goToNextPage,
    goToPreviousPage,
    resetPagination,
    canGoPrevious,
    pageSize,
  } = useCursorPagination(PAGE_SIZE)

  // ── Build API filters from search props ─────────────────────────────────
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
      history: true,
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

  // Reset pagination when filters change
  useEffect(() => {
    resetPagination()
  }, [
    search.status,
    search.risk_level,
    search.software_name,
    search.vendor,
    search.license_validity_period,
    search.data_access_impact,
    resetPagination,
  ])

  const { data, isLoading, error } = useSoftwareRequests(
    assetId,
    filters,
    currentCursor,
    pageSize,
  )

  // ── Navigation helpers ──────────────────────────────────────────────────
  const setSearchAndResetPage = useCallback(
    (updates: Partial<SoftwareRequestsTabProps['search']>) => {
      onSearchChange({ ...updates })
    },
    [onSearchChange],
  )

  // ── Dialog filter state (derived from search props) ─────────────────────
  const dialogFilters: DialogFilterState = useMemo(
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
    (f: DialogFilterState) => {
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

  // Count active dialog filters
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

  // ── Columns ─────────────────────────────────────────────────────────────
  const columns = useMemo<ColumnDef<SoftwareRequestListItem, any>[]>(
    () => [
      columnHelper.accessor('software_request_id', {
        header: 'REQUEST ID',
        cell: (info) => (
          <Link
            to="/assets/$asset_id/software-requests/$software_request_id"
            params={{
              asset_id: assetId,
              software_request_id: info.getValue(),
            }}
            className="text-sm font-medium text-info hover:underline"
          >
            {info.getValue()}
          </Link>
        ),
      }),
      columnHelper.accessor('software_name', {
        header: 'SOFTWARE NAME',
        cell: (info) => (
          <span className="text-sm font-medium">{info.getValue()}</span>
        ),
      }),
      columnHelper.accessor('version', {
        header: 'VERSION',
        cell: (info) => (
          <span className="text-sm font-medium">{info.getValue()}</span>
        ),
      }),
      columnHelper.accessor('vendor', {
        header: 'VENDOR',
        cell: (info) => (
          <span className="text-sm font-medium">{info.getValue()}</span>
        ),
      }),
      columnHelper.accessor('status', {
        header: 'STATUS',
        cell: (info) => <SoftwareStatusBadge status={info.getValue()} />,
      }),
      columnHelper.accessor('risk_level', {
        header: 'RISK LEVEL',
        cell: (info) => <RiskLevelBadge value={info.getValue()} />,
      }),
      columnHelper.accessor('data_access_impact', {
        header: 'DATA ACCESS IMPACT',
        cell: (info) => (
          <RiskLevelBadge
            value={info.getValue() as 'LOW' | 'MEDIUM' | 'HIGH' | null}
          />
        ),
      }),
      columnHelper.accessor('requested_by', {
        header: 'REQUESTED BY',
        cell: (info) => (
          <span className="text-sm font-medium">{info.getValue()}</span>
        ),
      }),
      columnHelper.accessor('created_at', {
        header: 'CREATED AT',
        cell: (info) => (
          <span className="text-sm font-medium text-muted-foreground">
            {formatDate(info.getValue()) || '—'}
          </span>
        ),
      }),
      columnHelper.display({
        id: 'actions',
        header: '',
        cell: (info) => (
          <div className="flex items-center justify-end">
            <Button size="icon" variant="ghost" asChild>
              <Link
                to="/assets/$asset_id/software-requests/$software_request_id"
                params={{
                  asset_id: assetId,
                  software_request_id: info.row.original.software_request_id,
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
    [assetId],
  )

  const tableData = useMemo(() => data?.items ?? [], [data])

  return (
    <div>
      {/* ── Toolbar ──────────────────────────────────────────────────── */}
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
    </div>
  )
}
