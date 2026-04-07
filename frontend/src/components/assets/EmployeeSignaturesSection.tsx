import { useMemo, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { createColumnHelper, type ColumnDef } from '@tanstack/react-table'
import { FileSignature, ExternalLink } from 'lucide-react'
import { useEmployeeSignatures } from '#/hooks/use-assets'
import { useCursorPagination } from '#/hooks/use-cursor-pagination'
import { DataTable } from '#/components/general/DataTable'
import { formatDate } from '#/lib/utils'
import type { SignatureItem } from '#/lib/models/types'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Badge } from '#/components/ui/badge'
import { Label } from '@/components/ui/label'
import {
  Empty,
  EmptyHeader,
  EmptyTitle,
  EmptyDescription,
} from '#/components/ui/empty'

const columnHelper = createColumnHelper<SignatureItem>()

export function EmployeeSignaturesSection({
  employeeId,
}: {
  employeeId: string
}) {
  // Cursor pagination state
  const {
    currentCursor,
    goToNextPage,
    goToPreviousPage,
    resetPagination,
    canGoPrevious,
    pageSize,
  } = useCursorPagination(10)

  // Applied filter state
  const [filters, setFilters] = useState<{
    assignment_date_from?: string
    assignment_date_to?: string
  }>({})

  // Dialog draft state
  const [filterOpen, setFilterOpen] = useState(false)
  const [draftFrom, setDraftFrom] = useState('')
  const [draftTo, setDraftTo] = useState('')

  const { data, isLoading, error } = useEmployeeSignatures(employeeId, {
    cursor: currentCursor,
    filters,
  })

  const columns = useMemo<ColumnDef<SignatureItem, any>[]>(
    () => [
      columnHelper.accessor('asset_id', {
        header: 'Asset ID',
        cell: (info) => (
          <Link
            to="/assets/$asset_id"
            params={{ asset_id: info.getValue() }}
            className="text-primary underline underline-offset-4 hover:text-primary/80"
          >
            {info.getValue()}
          </Link>
        ),
      }),
      columnHelper.accessor('brand', {
        header: 'Brand',
        cell: (info) => <span>{info.getValue() || '—'}</span>,
      }),
      columnHelper.accessor('model', {
        header: 'Model',
        cell: (info) => <span>{info.getValue() || '—'}</span>,
      }),
      columnHelper.accessor('assignment_date', {
        header: 'Assignment Date',
        cell: (info) => <span>{formatDate(info.getValue())}</span>,
      }),
      columnHelper.accessor('signature_timestamp', {
        header: 'Signed At',
        cell: (info) => <span>{formatDate(info.getValue())}</span>,
      }),
      columnHelper.accessor('signature_url', {
        header: 'Signature',
        cell: (info) => (
          <a
            href={info.getValue()}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-primary underline underline-offset-4 hover:text-primary/80"
          >
            <FileSignature className="size-4" />
            View
            <ExternalLink className="size-3" />
          </a>
        ),
      }),
    ],
    [],
  )

  const activeFilterCount =
    (filters.assignment_date_from ? 1 : 0) +
    (filters.assignment_date_to ? 1 : 0)

  const hasAnyFilter = activeFilterCount > 0

  function openFilterDialog() {
    setDraftFrom(filters.assignment_date_from ?? '')
    setDraftTo(filters.assignment_date_to ?? '')
    setFilterOpen(true)
  }

  function applyFilters() {
    setFilters({
      assignment_date_from: draftFrom || undefined,
      assignment_date_to: draftTo || undefined,
    })
    resetPagination()
    setFilterOpen(false)
  }

  function resetDraft() {
    setDraftFrom('')
    setDraftTo('')
  }

  function clearAllFilters() {
    setFilters({})
    resetPagination()
  }

  const items = data?.items ?? []
  const isEmpty = !isLoading && items.length === 0 && !error

  return (
    <div>
      {/* Toolbar */}
      <div className="flex items-center gap-3 mt-3">
        <Button variant="outline" size="sm" onClick={openFilterDialog}>
          Filters
          {activeFilterCount > 0 && (
            <Badge variant="default" size="sm" className="ml-1.5">
              {activeFilterCount}
            </Badge>
          )}
        </Button>
        {hasAnyFilter && (
          <Button variant="ghost" size="sm" onClick={clearAllFilters}>
            Clear all
          </Button>
        )}
      </div>

      {/* Filter Dialog */}
      <Dialog open={filterOpen} onOpenChange={setFilterOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Filter Signatures</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 -mx-1 px-1">
            <div className="grid gap-2">
              <Label htmlFor="filter-date-from">Assignment Date From</Label>
              <Input
                id="filter-date-from"
                type="date"
                value={draftFrom}
                onChange={(e) => setDraftFrom(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="filter-date-to">Assignment Date To</Label>
              <Input
                id="filter-date-to"
                type="date"
                value={draftTo}
                onChange={(e) => setDraftTo(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={resetDraft}>
              Reset
            </Button>
            <Button onClick={applyFilters}>Apply Filters</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Table or Empty State */}
      {isEmpty ? (
        <Empty className="mt-4">
          <EmptyHeader>
            <EmptyTitle>No handover signatures on record.</EmptyTitle>
            <EmptyDescription>
              Signatures will appear here once the employee accepts asset
              handovers.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        <DataTable
          columns={columns}
          data={items}
          pageSize={pageSize}
          entityName="signatures"
          isLoading={isLoading}
          error={
            error instanceof Error
              ? error.message
              : error
                ? String(error)
                : undefined
          }
          hasNextPage={data?.has_next_page ?? false}
          canGoPrevious={canGoPrevious}
          onNextPage={() => data?.next_cursor && goToNextPage(data.next_cursor)}
          onPreviousPage={goToPreviousPage}
        />
      )}
    </div>
  )
}
