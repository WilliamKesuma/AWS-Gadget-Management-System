import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { Skeleton } from '#/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination'
import { Card } from '@/components/ui/card'

interface DataTableProps<TData> {
  columns: ColumnDef<TData, any>[]
  data: TData[]
  pageSize?: number
  entityName?: string
  isLoading?: boolean
  error?: string
  hasNextPage?: boolean
  canGoPrevious?: boolean
  onNextPage?: () => void
  onPreviousPage?: () => void
}

export function DataTable<TData>({
  columns,
  data,
  pageSize = 10,
  entityName = 'items',
  isLoading = false,
  error,
  hasNextPage = false,
  canGoPrevious = false,
  onNextPage,
  onPreviousPage,
}: DataTableProps<TData>) {
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  const showPagination = canGoPrevious || hasNextPage

  return (
    <Card className="gap-0 py-0 flex flex-col mt-2">
      <div className="w-full relative px-2 py-1 overflow-x-auto min-h-[200px]">
        {error ? (
          <div className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-2 bg-card/90 backdrop-blur-sm rounded-lg m-2">
            <div className="flex flex-col items-center gap-1.5 text-center">
              <div className="size-10 rounded-full bg-danger-subtle flex items-center justify-center mb-1">
                <svg
                  className="size-5 text-danger"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                  />
                </svg>
              </div>
              <p className="text-sm font-semibold text-foreground">
                Failed to load {entityName}
              </p>
              <p className="text-xs text-muted-foreground max-w-xs">{error}</p>
            </div>
          </div>
        ) : null}
        <Table>
          <TableHeader className="bg-transparent hover:bg-transparent">
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow
                key={headerGroup.id}
                className="hover:bg-transparent"
              >
                {headerGroup.headers.map((header) => (
                  <TableHead
                    key={header.id}
                    className="text-[11px] font-bold text-muted-foreground tracking-wider uppercase h-12 align-middle px-4"
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody className="[&_tr:last-child]:border-0 font-medium">
            {isLoading ? (
              Array.from({ length: pageSize > 5 ? 5 : pageSize }).map(
                (_, i) => (
                  <TableRow
                    key={`skeleton-${i}`}
                  >
                    {columns.map((_, j) => (
                      <TableCell key={j} className="py-3 px-4 align-middle">
                        <Skeleton
                          className="h-4 w-full"
                          style={{ width: `${60 + ((i * 3 + j * 7) % 35)}%` }}
                        />
                      </TableCell>
                    ))}
                  </TableRow>
                ),
              )
            ) : table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && 'selected'}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell
                      key={cell.id}
                      className="py-2.5 px-4 align-middle"
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : !error && !isLoading ? (
              <TableRow className="hover:bg-transparent">
                <TableCell
                  colSpan={columns.length}
                  className="h-40 text-center"
                >
                  <div className="flex flex-col items-center justify-center gap-2 py-6 text-muted-foreground">
                    <div className="size-10 rounded-full bg-muted flex items-center justify-center mb-1">
                      <svg
                        className="size-5 text-muted-foreground/60"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={1.5}
                        aria-hidden="true"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M3.75 9.776c.112-.017.227-.026.344-.026h15.812c.117 0 .232.009.344.026m-16.5 0a2.25 2.25 0 0 0-1.883 2.542l.857 6a2.25 2.25 0 0 0 2.227 1.932H19.05a2.25 2.25 0 0 0 2.227-1.932l.857-6a2.25 2.25 0 0 0-1.883-2.542m-16.5 0V6A2.25 2.25 0 0 1 6 3.75h3.879a1.5 1.5 0 0 1 1.06.44l2.122 2.12a1.5 1.5 0 0 0 1.06.44H18A2.25 2.25 0 0 1 20.25 9v.776"
                        />
                      </svg>
                    </div>
                    <p className="text-sm font-medium text-foreground">
                      No {entityName} found
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Try adjusting your filters or search terms.
                    </p>
                  </div>
                </TableCell>
              </TableRow>
            ) : null}
          </TableBody>
        </Table>
      </div>

      {showPagination && (
        <div className="flex items-center justify-end px-6 py-4 border-t bg-muted/30 rounded-b-xl">
          <Pagination className="justify-end w-auto mx-0">
            <PaginationContent className="gap-1.5">
              <PaginationItem>
                <PaginationPrevious
                  href="#"
                  onClick={(e) => {
                    e.preventDefault()
                    if (canGoPrevious) onPreviousPage?.()
                  }}
                  aria-disabled={!canGoPrevious}
                  className={
                    !canGoPrevious
                      ? 'pointer-events-none opacity-50'
                      : 'cursor-pointer'
                  }
                />
              </PaginationItem>
              <PaginationItem>
                <PaginationNext
                  href="#"
                  onClick={(e) => {
                    e.preventDefault()
                    if (hasNextPage) onNextPage?.()
                  }}
                  aria-disabled={!hasNextPage}
                  className={
                    !hasNextPage
                      ? 'pointer-events-none opacity-50'
                      : 'cursor-pointer'
                  }
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        </div>
      )}
    </Card>
  )
}
