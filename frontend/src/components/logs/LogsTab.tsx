import { useMemo } from 'react'
import { createColumnHelper, type ColumnDef } from '@tanstack/react-table'
import { DataTable } from '#/components/general/DataTable'
import { Badge } from '#/components/ui/badge'
import { useAssetLogs } from '#/hooks/use-audit-logs'
import { useCursorPagination } from '#/hooks/use-cursor-pagination'
import { formatDate } from '#/lib/utils'
import { AssetStatusLabels } from '#/lib/models/labels'
import type { AuditLogItem, AssetStatus } from '#/lib/models/types'

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Look up a human-readable label for an asset status, falling back to the raw value. */
function statusLabel(raw: string): string {
    return AssetStatusLabels[raw as AssetStatus] ?? raw
}

/** Convert UPPER_SNAKE phase strings to Title Case (e.g. "ASSET_CREATION" → "Asset Creation"). */
function humanizePhase(raw: string): string {
    return raw
        .split('_')
        .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
        .join(' ')
}

// ── Column definitions (module scope) ────────────────────────────────────────

const columnHelper = createColumnHelper<AuditLogItem>()

const columns: ColumnDef<AuditLogItem, any>[] = [
    columnHelper.accessor('timestamp', {
        header: 'TIMESTAMP',
        cell: (info) => (
            <span className="text-sm text-muted-foreground">
                {formatDate(info.getValue()) || '—'}
            </span>
        ),
    }),
    columnHelper.accessor('phase', {
        header: 'PHASE',
        cell: (info) => (
            <Badge variant="info">{humanizePhase(info.getValue())}</Badge>
        ),
    }),
    columnHelper.accessor('previous_status', {
        header: 'PREVIOUS STATUS',
        cell: (info) => {
            const raw = info.getValue()
            if (!raw) return <span className="text-sm text-muted-foreground">—</span>
            return <Badge variant="secondary">{statusLabel(raw)}</Badge>
        },
    }),
    columnHelper.accessor('new_status', {
        header: 'NEW STATUS',
        cell: (info) => (
            <Badge variant="outline">{statusLabel(info.getValue())}</Badge>
        ),
    }),
    columnHelper.accessor('actor_name', {
        header: 'ACTOR',
        cell: (info) => <span className="text-sm">{info.getValue()}</span>,
    }),
    columnHelper.accessor('remarks', {
        header: 'REMARKS',
        cell: (info) => {
            const value = info.getValue()
            if (!value)
                return <span className="text-sm text-muted-foreground">—</span>
            const truncated = value.length > 60 ? `${value.slice(0, 60)}…` : value
            return (
                <span className="text-sm truncate max-w-[200px] block" title={value}>
                    {truncated}
                </span>
            )
        },
    }),
    columnHelper.accessor('rejection_reason', {
        header: 'REJECTION REASON',
        cell: (info) => {
            const value = info.getValue()
            if (!value)
                return <span className="text-sm text-muted-foreground">—</span>
            const truncated = value.length > 60 ? `${value.slice(0, 60)}…` : value
            return (
                <span
                    className="text-sm text-danger truncate max-w-[200px] block"
                    title={value}
                >
                    {truncated}
                </span>
            )
        },
    }),
]

// ── LogsTab ──────────────────────────────────────────────────────────────────

type Props = {
    assetId: string
}

const PAGE_SIZE = 10

export function LogsTab({ assetId }: Props) {
    const {
        currentCursor,
        goToNextPage,
        goToPreviousPage,
        canGoPrevious,
        pageSize,
    } = useCursorPagination(PAGE_SIZE)

    const { data, isLoading, error } = useAssetLogs(
        assetId,
        currentCursor,
        pageSize,
    )
    const tableData = useMemo(() => data?.items ?? [], [data])

    return (
        <DataTable
            columns={columns}
            data={tableData}
            entityName="logs"
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
