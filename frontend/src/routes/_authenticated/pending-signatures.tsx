import { useMemo } from 'react'
import {
  createFileRoute,
  redirect,
  Link,
} from '@tanstack/react-router'
import { createColumnHelper, type ColumnDef } from '@tanstack/react-table'
import { z } from 'zod'
import { Eye } from 'lucide-react'
import type {
  UserRole,
  PendingSignatureItem,
  ReturnTrigger,
} from '#/lib/models/types'
import {
  getBaseMeta,
  getPageMeta,
  getCanonicalLink,
  type SeoPageInput,
} from '../../lib/seo'
import { usePendingSignatures } from '#/hooks/use-returns'
import { useCursorPagination } from '#/hooks/use-cursor-pagination'
import { hasRole } from '#/lib/permissions'
import { formatDate } from '#/lib/utils'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { DataTable } from '#/components/general/DataTable'
import { ReturnTriggerLabels } from '#/lib/models/labels'

// ── SEO ───────────────────────────────────────────────────────────────────────

const PENDING_SIGNATURES_SEO = {
  title: 'Pending Signatures',
  description:
    'View documents awaiting your signature, including asset handover forms and return acknowledgements.',
  path: '/pending-signatures',
} satisfies SeoPageInput

// ── Route config ──────────────────────────────────────────────────────────────

const ALLOWED: UserRole[] = ['employee']

const PAGE_SIZE = 10

export const Route = createFileRoute(
  '/_authenticated/pending-signatures' as any,
)({
  validateSearch: (raw: Record<string, unknown>) =>
    z.object({}).parse(raw),
  beforeLoad: ({ context }) => {
    if (
      !hasRole(
        (context as { userRole?: UserRole | null }).userRole ?? null,
        ALLOWED,
      )
    ) {
      throw redirect({ to: '/unauthorized' })
    }
  },
  component: PendingSignaturesPage,
  head: () => ({
    meta: [
      ...getBaseMeta(),
      { name: 'robots', content: 'noindex, nofollow' },
      ...getPageMeta(PENDING_SIGNATURES_SEO),
    ],
    links: [getCanonicalLink(PENDING_SIGNATURES_SEO.path)],
  }),
})

// ── Column definitions ────────────────────────────────────────────────────────

const columnHelper = createColumnHelper<PendingSignatureItem>()

// ── Component ─────────────────────────────────────────────────────────────────

function PendingSignaturesPage() {
  const {
    currentCursor,
    goToNextPage,
    goToPreviousPage,
    canGoPrevious,
    pageSize,
  } = useCursorPagination(PAGE_SIZE)

  const { data, isLoading, error } = usePendingSignatures(currentCursor, pageSize)

  const columns = useMemo<ColumnDef<PendingSignatureItem, any>[]>(
    () => [
      columnHelper.accessor('document_type', {
        header: 'TYPE',
        cell: (info) => {
          const type = info.getValue()
          return (
            <Badge variant={type === 'return' ? 'info' : 'default'}>
              {type === 'return' ? 'Return' : 'Handover'}
            </Badge>
          )
        },
      }),
      columnHelper.accessor('asset_id', {
        header: 'ASSET ID',
        cell: (info) => <span>{info.getValue()}</span>,
      }),
      columnHelper.accessor('return_trigger', {
        header: 'RETURN TRIGGER',
        cell: (info) => {
          const val = info.getValue() as ReturnTrigger | undefined
          return <span>{val ? (ReturnTriggerLabels[val] ?? '—') : '—'}</span>
        },
      }),
      columnHelper.accessor('initiated_at', {
        header: 'INITIATED AT',
        cell: (info) => <span>{formatDate(info.getValue()) || '—'}</span>,
      }),
      columnHelper.display({
        id: 'actions',
        header: '',
        cell: (info) => {
          const row = info.row.original
          const isReturn = row.document_type === 'return'
          return (
            <div className="flex items-center justify-end gap-2">
              <Button asChild variant="ghost" size="icon">
                {isReturn ? (
                  <Link
                    to="/assets/$asset_id/returns/$return_id"
                    params={
                      {
                        asset_id: row.asset_id,
                        return_id: row.record_id,
                      } as any
                    }
                  >
                    <Eye className="size-4" />
                  </Link>
                ) : (
                  <Link
                    to="/assets/$asset_id"
                    params={{ asset_id: row.asset_id }}
                  >
                    <Eye className="size-4" />
                  </Link>
                )}
              </Button>
            </div>
          )
        },
      }),
    ],
    [],
  )

  const tableData = useMemo(() => data?.items ?? [], [data])

  return (
    <main className="page-base">
      <div>
        <h1 className="page-title">Pending Signatures</h1>
        <p className="page-subtitle">Documents awaiting your signature.</p>
      </div>

      {error && (
        <div className="alert-danger mt-4">{(error as Error).message}</div>
      )}

      <div className="mt-4">
        <DataTable
          columns={columns}
          data={tableData}
          isLoading={isLoading}
          pageSize={pageSize}
          entityName="pending signatures"
          hasNextPage={data?.has_next_page ?? false}
          canGoPrevious={canGoPrevious}
          onNextPage={() => data?.next_cursor && goToNextPage(data.next_cursor)}
          onPreviousPage={goToPreviousPage}
        />
      </div>
    </main>
  )
}
