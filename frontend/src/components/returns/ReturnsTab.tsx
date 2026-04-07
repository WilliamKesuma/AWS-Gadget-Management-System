import { useState, useMemo, useCallback, useEffect } from 'react'
import { createColumnHelper, type ColumnDef } from '@tanstack/react-table'
import { Eye } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'
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
import { ReturnConditionBadge } from './ReturnConditionBadge'
import { ResetStatusBadge } from './ResetStatusBadge'
import { ReturnStatusBadge } from './ReturnStatusBadge'
import { useReturns } from '#/hooks/use-returns'
import { useCursorPagination } from '#/hooks/use-cursor-pagination'
import { ReturnTriggerLabels, ReturnConditionLabels } from '#/lib/models/labels'
import { formatDate } from '#/lib/utils'
import type {
  ReturnListItem,
  ReturnTrigger,
  ReturnCondition,
} from '#/lib/models/types'

// ── Column definitions (module scope) ────────────────────────────────────────

const columnHelper = createColumnHelper<ReturnListItem>()

const columns: ColumnDef<ReturnListItem, any>[] = [
  columnHelper.accessor('return_id', {
    header: 'RETURN ID',
    cell: (info) => (
      <Link
        to={'/assets/$asset_id/returns/$return_id'}
        params={{
          asset_id: info.row.original.asset_id,
          return_id: info.getValue(),
        } as any}
        className="text-sm font-medium text-info hover:underline"
      >
        {info.getValue()}
      </Link>
    ),
  }),
  columnHelper.accessor('return_trigger', {
    header: 'RETURN TRIGGER',
    cell: (info) => (
      <span className="text-sm font-medium">
        {ReturnTriggerLabels[info.getValue<ReturnTrigger>()]}
      </span>
    ),
  }),
  columnHelper.accessor('condition_assessment', {
    header: 'CONDITION',
    cell: (info) => <ReturnConditionBadge condition={info.getValue()} />,
  }),
  columnHelper.accessor('reset_status', {
    header: 'RESET STATUS',
    cell: (info) => <ResetStatusBadge status={info.getValue()} />,
  }),
  columnHelper.accessor('initiated_by', {
    header: 'INITIATED BY',
    cell: (info) => <span className="text-sm">{info.getValue()}</span>,
  }),
  columnHelper.accessor('initiated_at', {
    header: 'INITIATED AT',
    cell: (info) => (
      <span className="text-sm text-muted-foreground">
        {formatDate(info.getValue()) || '—'}
      </span>
    ),
  }),
  columnHelper.accessor('resolved_status', {
    header: 'STATUS',
    cell: (info) => <ReturnStatusBadge status={info.getValue()} />,
  }),
  columnHelper.accessor('completed_at', {
    header: 'COMPLETED AT',
    cell: (info) => (
      <span className="text-sm text-muted-foreground">
        {formatDate(info.getValue()) || '—'}
      </span>
    ),
  }),
  columnHelper.display({
    id: 'actions',
    header: '',
    cell: ({ row }) => (
      <div className="flex items-center justify-end">
        <Button size="icon" variant="ghost" asChild>
          <Link
            to="/assets/$asset_id/returns/$return_id"
            params={{
              asset_id: row.original.asset_id,
              return_id: row.original.return_id,
            }}
            aria-label="View details"
          >
            <Eye className="size-4" />
          </Link>
        </Button>
      </div>
    ),
  }),
]

// ── Filter dialog ─────────────────────────────────────────────────────────────

type FilterState = {
  return_trigger: ReturnTrigger | 'all'
  condition_assessment: ReturnCondition | 'all'
}

const EMPTY_FILTERS: FilterState = {
  return_trigger: 'all',
  condition_assessment: 'all',
}

function ReturnsFilterDialog({
  open,
  onOpenChange,
  current,
  onApply,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  current: FilterState
  onApply: (f: FilterState) => void
}) {
  const [draft, setDraft] = useState<FilterState>(current)

  const handleOpenChange = (next: boolean) => {
    if (next) setDraft(current)
    onOpenChange(next)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Filter Returns</DialogTitle>
          <DialogDescription>
            Narrow down the returns list by trigger or condition.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 -mx-1 px-1">
          <div className="space-y-1.5">
            <Label htmlFor="filter-trigger">Return Trigger</Label>
            <Select
              value={draft.return_trigger}
              onValueChange={(v) =>
                setDraft((d) => ({
                  ...d,
                  return_trigger: v as ReturnTrigger | 'all',
                }))
              }
            >
              <SelectTrigger id="filter-trigger" className="w-full">
                <SelectValue placeholder="All Triggers" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Triggers</SelectItem>
                {(Object.keys(ReturnTriggerLabels) as ReturnTrigger[]).map(
                  (t) => (
                    <SelectItem key={t} value={t}>
                      {ReturnTriggerLabels[t]}
                    </SelectItem>
                  ),
                )}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="filter-condition">Condition Assessment</Label>
            <Select
              value={draft.condition_assessment}
              onValueChange={(v) =>
                setDraft((d) => ({
                  ...d,
                  condition_assessment: v as ReturnCondition | 'all',
                }))
              }
            >
              <SelectTrigger id="filter-condition" className="w-full">
                <SelectValue placeholder="All Conditions" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Conditions</SelectItem>
                {(Object.keys(ReturnConditionLabels) as ReturnCondition[]).map(
                  (c) => (
                    <SelectItem key={c} value={c}>
                      {ReturnConditionLabels[c]}
                    </SelectItem>
                  ),
                )}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => setDraft(EMPTY_FILTERS)}>
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

// ── ReturnsTab ────────────────────────────────────────────────────────────────

type Props = {
  assetId: string
  search: {
    ret_trigger?: ReturnTrigger
    ret_condition?: ReturnCondition
  }
  onSearchChange: (updates: Record<string, unknown>) => void
}

const PAGE_SIZE = 10

export function ReturnsTab({ assetId, search, onSearchChange }: Props) {
  const [filterOpen, setFilterOpen] = useState(false)
  const {
    currentCursor,
    goToNextPage,
    goToPreviousPage,
    resetPagination,
    canGoPrevious,
    pageSize,
  } = useCursorPagination(PAGE_SIZE)

  const filters = useMemo(
    () => ({
      ...(search.ret_trigger && { return_trigger: search.ret_trigger }),
      ...(search.ret_condition && {
        condition_assessment: search.ret_condition,
      }),
      history: true,
    }),
    [search.ret_trigger, search.ret_condition],
  )

  // Reset pagination when filters change
  useEffect(() => {
    resetPagination()
  }, [search.ret_trigger, search.ret_condition, resetPagination])

  const { data, isLoading, error } = useReturns(
    assetId,
    filters,
    currentCursor,
    pageSize,
  )
  const tableData = useMemo(() => data?.items ?? [], [data])

  const currentDialogFilters: FilterState = {
    return_trigger: search.ret_trigger ?? 'all',
    condition_assessment: search.ret_condition ?? 'all',
  }

  const dialogFilterCount = [search.ret_trigger, search.ret_condition].filter(
    Boolean,
  ).length
  const hasAnyFilter = dialogFilterCount > 0

  const handleApply = useCallback(
    (f: FilterState) => {
      onSearchChange({
        ret_trigger: f.return_trigger === 'all' ? undefined : f.return_trigger,
        ret_condition:
          f.condition_assessment === 'all' ? undefined : f.condition_assessment,
      })
    },
    [onSearchChange],
  )

  const clearAllFilters = useCallback(() => {
    onSearchChange({
      ret_trigger: undefined,
      ret_condition: undefined,
    })
  }, [onSearchChange])

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
        entityName="returns"
        isLoading={isLoading}
        error={error ? (error as Error).message : undefined}
        pageSize={pageSize}
        hasNextPage={data?.has_next_page ?? false}
        canGoPrevious={canGoPrevious}
        onNextPage={() => data?.next_cursor && goToNextPage(data.next_cursor)}
        onPreviousPage={goToPreviousPage}
      />

      <ReturnsFilterDialog
        open={filterOpen}
        onOpenChange={setFilterOpen}
        current={currentDialogFilters}
        onApply={handleApply}
      />
    </>
  )
}
