import { useMemo } from 'react'
import { Link } from '@tanstack/react-router'
import { createColumnHelper, type ColumnDef } from '@tanstack/react-table'
import { Eye } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { DataTable } from '#/components/general/DataTable'
import { usePendingDisposals } from '#/hooks/use-disposals'
import { useCursorPagination } from '#/hooks/use-cursor-pagination'
import { formatDate } from '#/lib/utils'
import type { PendingDisposalItem } from '#/lib/models/types'

// ── Column helper ─────────────────────────────────────────────────────────────

const columnHelper = createColumnHelper<PendingDisposalItem>()
const PAGE_SIZE = 10

// ── Component ─────────────────────────────────────────────────────────────────

type DisposalsTabContentProps = {
  history?: boolean
}

export function DisposalsTabContent({
  history = false,
}: DisposalsTabContentProps) {
  const {
    currentCursor,
    goToNextPage,
    goToPreviousPage,
    canGoPrevious,
    pageSize,
  } = useCursorPagination(PAGE_SIZE)

  const { data, isLoading, error } = usePendingDisposals(
    currentCursor,
    pageSize,
    history,
  )

  const tableData = useMemo(() => data?.items ?? [], [data])

  const columns = useMemo<ColumnDef<PendingDisposalItem, any>[]>(
    () => [
      columnHelper.accessor('disposal_id', {
        header: 'DISPOSAL ID',
        cell: (info) => (
          <Link
            to={'/assets/$asset_id/disposals/$disposal_id' as any}
            params={
              {
                asset_id: info.row.original.asset_id,
                disposal_id: info.getValue(),
              } as any
            }
            className="text-sm font-medium text-info hover:underline"
          >
            {info.getValue()}
          </Link>
        ),
      }),
      columnHelper.accessor('asset_id', {
        header: 'ASSET ID',
        cell: (info) => (
          <Link
            to={'/assets/$asset_id/disposals/$disposal_id' as any}
            params={
              {
                asset_id: info.row.original.asset_id,
                disposal_id: info.row.original.disposal_id,
              } as any
            }
            className="text-sm font-medium text-info hover:underline"
          >
            {info.getValue()}
          </Link>
        ),
      }),
      columnHelper.display({
        id: 'brand_model',
        header: 'BRAND / MODEL',
        cell: (info) => {
          const specs = info.row.original.asset_specs
          const brand = specs?.brand ?? null
          const model = specs?.model ?? null
          if (!brand && !model) return <span className="text-sm">N/A</span>
          return (
            <span className="text-sm font-medium">
              {brand ?? 'N/A'} {model ?? 'N/A'}
            </span>
          )
        },
      }),
      columnHelper.display({
        id: 'serial_number',
        header: 'SERIAL NUMBER',
        cell: (info) => (
          <span className="text-sm">
            {info.row.original.asset_specs?.serial_number ?? 'N/A'}
          </span>
        ),
      }),
      columnHelper.accessor('disposal_reason', {
        header: 'DISPOSAL REASON',
        cell: (info) => (
          <span className="text-sm font-medium">{info.getValue()}</span>
        ),
      }),
      columnHelper.accessor('justification', {
        header: 'JUSTIFICATION',
        cell: (info) => {
          const value = info.getValue()
          const truncated =
            value && value.length > 50 ? `${value.slice(0, 50)}…` : value
          return (
            <span
              className="text-sm truncate max-w-[200px] block"
              title={value}
            >
              {truncated}
            </span>
          )
        },
      }),
      columnHelper.accessor('initiated_by', {
        header: 'INITIATED BY',
        cell: (info) => (
          <span className="text-sm font-medium">{info.getValue()}</span>
        ),
      }),
      columnHelper.accessor('initiated_at', {
        header: 'INITIATED AT',
        cell: (info) => (
          <span className="text-sm text-muted-foreground">
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
                to={'/assets/$asset_id/disposals/$disposal_id' as any}
                params={
                  {
                    asset_id: info.row.original.asset_id,
                    disposal_id: info.row.original.disposal_id,
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

  return (
    <DataTable
      columns={columns}
      data={tableData}
      entityName="pending disposal requests"
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
