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
import { DisposalStatusBadge } from './DisposalStatusBadge'
import { useDisposals } from '#/hooks/use-disposals'
import { DisposalStatusLabels } from '#/lib/models/labels'
import { useCursorPagination } from '#/hooks/use-cursor-pagination'
import { formatDate } from '#/lib/utils'
import type { DisposalListItem, DisposalStatus } from '#/lib/models/types'

// ── Column definitions (module scope) ────────────────────────────────────────

const columnHelper = createColumnHelper<DisposalListItem>()

const columns: ColumnDef<DisposalListItem, any>[] = [
    columnHelper.accessor('disposal_id', {
        header: 'DISPOSAL ID',
        cell: (info) => (
            <Link
                to={'/assets/$asset_id/disposals/$disposal_id' as any}
                params={{
                    asset_id: info.row.original.asset_id,
                    disposal_id: info.getValue(),
                } as any}
                className="text-sm font-medium text-info hover:underline"
            >
                {info.getValue()}
            </Link>
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
                <span className="text-sm truncate max-w-[200px] block" title={value}>
                    {truncated}
                </span>
            )
        },
    }),
    columnHelper.accessor('status', {
        header: 'STATUS',
        cell: (info) => <DisposalStatusBadge status={info.getValue()} />,
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
    columnHelper.accessor('disposal_date', {
        header: 'DISPOSAL DATE',
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
                        to={'/assets/$asset_id/disposals/$disposal_id' as any}
                        params={{
                            asset_id: row.original.asset_id,
                            disposal_id: row.original.disposal_id,
                        } as any}
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
    status: DisposalStatus | 'all'
}

const EMPTY_FILTERS: FilterState = {
    status: 'all',
}

function DisposalsFilterDialog({
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
                    <DialogTitle>Filter Disposals</DialogTitle>
                    <DialogDescription>
                        Narrow down the disposals list by status.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 -mx-1 px-1">
                    <div className="space-y-1.5">
                        <Label htmlFor="filter-disposal-status">Status</Label>
                        <Select
                            value={draft.status}
                            onValueChange={(v) =>
                                setDraft((d) => ({
                                    ...d,
                                    status: v as DisposalStatus | 'all',
                                }))
                            }
                        >
                            <SelectTrigger id="filter-disposal-status" className="w-full">
                                <SelectValue placeholder="All Statuses" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All Statuses</SelectItem>
                                {(Object.keys(DisposalStatusLabels) as DisposalStatus[]).map(
                                    (s) => (
                                        <SelectItem key={s} value={s}>
                                            {DisposalStatusLabels[s]}
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

// ── DisposalsTab ──────────────────────────────────────────────────────────────

type Props = {
    assetId: string
    search: {
        disp_status?: DisposalStatus
    }
    onSearchChange: (updates: Record<string, unknown>) => void
}

const PAGE_SIZE = 10

export function DisposalsTab({ assetId, search, onSearchChange }: Props) {
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
            asset_id: assetId,
            ...(search.disp_status && { status: search.disp_status }),
            history: true,
        }),
        [assetId, search.disp_status],
    )

    // Reset pagination when filters change
    useEffect(() => {
        resetPagination()
    }, [search.disp_status, resetPagination])

    const { data, isLoading, error } = useDisposals(filters, currentCursor, pageSize)
    const tableData = useMemo(() => data?.items ?? [], [data])

    const currentDialogFilters: FilterState = {
        status: search.disp_status ?? 'all',
    }

    const dialogFilterCount = [search.disp_status].filter(Boolean).length
    const hasAnyFilter = dialogFilterCount > 0

    const handleApply = useCallback(
        (f: FilterState) => {
            onSearchChange({
                disp_status: f.status === 'all' ? undefined : f.status,
            })
        },
        [onSearchChange],
    )

    const clearAllFilters = useCallback(() => {
        onSearchChange({
            disp_status: undefined,
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
                entityName="disposals"
                isLoading={isLoading}
                error={error ? (error as Error).message : undefined}
                pageSize={pageSize}
                hasNextPage={data?.has_next_page ?? false}
                canGoPrevious={canGoPrevious}
                onNextPage={() => data?.next_cursor && goToNextPage(data.next_cursor)}
                onPreviousPage={goToPreviousPage}
            />

            <DisposalsFilterDialog
                open={filterOpen}
                onOpenChange={setFilterOpen}
                current={currentDialogFilters}
                onApply={handleApply}
            />
        </>
    )
}
