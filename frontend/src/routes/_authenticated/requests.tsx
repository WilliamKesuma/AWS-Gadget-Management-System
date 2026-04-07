import { useState, useMemo, useCallback } from 'react'
import {
  createFileRoute,
  redirect,
  useNavigate,
  Link,
  Outlet,
  useMatchRoute,
} from '@tanstack/react-router'
import { z } from 'zod'
import { createColumnHelper, type ColumnDef } from '@tanstack/react-table'
import {
  CheckCircle2,
  CheckCircle,
  AlertTriangle,
  Eye,
  CalendarIcon,
  ClipboardList,
  CheckCircle2Icon,
  CalendarCheck2,
} from 'lucide-react'
import type {
  UserRole,
  AllIssueListItem,
  IssueStatus,
  IssueCategory,
  TabDef,
  SoftwareRequestListItem,
  SoftwareStatus,
  DataAccessImpact,
  ListSoftwareRequestsFilter,
  ListAllIssuesFilter,
  DisposalListItem,
  DisposalStatus,
  ListDisposalsFilter,
  AllReturnListItem,
  ListAllReturnsFilter,
  ReturnTrigger,
  SortOrder,
} from '#/lib/models/types'
import {
  CATEGORY_VALUES,
  IssueStatusSchema,
  IssueCategorySchema,
  DisposalStatusSchema,
  SoftwareStatusSchema,
  RiskLevelSchema,
  DataAccessImpactSchema,
  SortOrderSchema,
} from '#/lib/models/types'
import {
  getBaseMeta,
  getPageMeta,
  getCanonicalLink,
  type SeoPageInput,
} from '../../lib/seo'
import { useCursorPagination } from '#/hooks/use-cursor-pagination'
import { useCurrentUserRole } from '#/hooks/use-current-user'
import { hasRole } from '#/lib/permissions'
import { useAllIssues } from '#/hooks/use-issues'
import { useAllSoftwareRequests } from '#/hooks/use-software-requests'
import { useAllReturns } from '#/hooks/use-returns'
import { cn, formatDate, formatNumber } from '#/lib/utils'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import { Switch } from '#/components/ui/switch'
import { StatCard } from '#/components/general/StatCard'
import {
  useRequestsITAdminStats,
  useRequestsEmployeeStats,
} from '#/hooks/use-page-stats'
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
import { IssueStatusBadge } from '#/components/issues/IssueStatusBadge'
import { SoftwareStatusBadge } from '#/components/software/SoftwareStatusBadge'
import { RiskLevelBadge } from '#/components/software/RiskLevelBadge'
import {
  RiskLevelLabels,
  SoftwareStatusLabels,
  IssueStatusLabels,
  IssueCategoryLabels,
  DisposalStatusLabels,
} from '#/lib/models/labels'
import { IssueCategoryVariants } from '#/lib/models/badge-variants'
import { ReturnTriggerLabels } from '#/lib/models/labels'
import { ReturnConditionBadge } from '#/components/returns/ReturnConditionBadge'
import { ReturnStatusBadge } from '#/components/returns/ReturnStatusBadge'
import { ResetStatusBadge } from '#/components/returns/ResetStatusBadge'
import { format } from 'date-fns'
import { DisposalStatusBadge } from '#/components/disposals/DisposalStatusBadge'
import { useDisposals } from '#/hooks/use-disposals'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '#/components/ui/popover'
import { Calendar } from '#/components/ui/calendar'

// ── SEO ───────────────────────────────────────────────────────────────────────

const MAINTENANCE_SEO = {
  title: 'Maintenance Hub',
  description:
    'Manage IT infrastructure repair tickets, schedule maintenance windows, and track resolution progress across all organization gadgets.',
  path: '/requests',
} satisfies SeoPageInput

// ── Route config ──────────────────────────────────────────────────────────────

const REQUESTS_ALLOWED: UserRole[] = ['it-admin', 'management', 'employee']

const maintenanceSearchSchema = z.object({
  tab: z
    .enum([
      ...CATEGORY_VALUES,
      'requests',
      'ongoing',
      'history',
      'all',
      'pending',
      'in-review',
      'approved',
      'rejected',
      'returns',
      'disposals',
    ] as const)
    .optional(),
  history: z.coerce.boolean().optional(),
  status: SoftwareStatusSchema.optional(),
  risk_level: RiskLevelSchema.optional(),
  software_name: z.string().optional(),
  vendor: z.string().optional(),
  license_validity_period: z.string().optional(),
  data_access_impact: DataAccessImpactSchema.optional(),
  // Disposal filters
  disposal_status: DisposalStatusSchema.optional(),
  disposal_reason: z.string().optional(),
  date_from: z.string().optional(),
  date_to: z.string().optional(),
  // Issues filters
  issue_status: IssueStatusSchema.optional(),
  issue_category: IssueCategorySchema.optional(),
  issue_sort_order: SortOrderSchema.optional(),
})

export const Route = createFileRoute('/_authenticated/requests')({
  validateSearch: (raw: Record<string, unknown>) =>
    maintenanceSearchSchema.parse(raw),
  beforeLoad: ({ context }) => {
    if (!hasRole(context.userRole, REQUESTS_ALLOWED)) {
      throw redirect({ to: '/unauthorized' })
    }
  },
  component: MaintenancePage,
  head: () => ({
    meta: [
      ...getBaseMeta(),
      { name: 'robots', content: 'noindex, nofollow' },
      ...getPageMeta(MAINTENANCE_SEO),
    ],
    links: [getCanonicalLink(MAINTENANCE_SEO.path)],
  }),
})

// ── Status groupings ──────────────────────────────────────────────────────────

// ── Column definitions (module scope — not inside render) ─────────────────────

const itAdminColumnHelper = createColumnHelper<AllIssueListItem>()
const softwareColumnHelper = createColumnHelper<SoftwareRequestListItem>()
const allReturnsColumnHelper = createColumnHelper<AllReturnListItem>()

const PAGE_SIZE = 10

const itAdminColumns: ColumnDef<AllIssueListItem, any>[] = [
  itAdminColumnHelper.accessor('issue_id', {
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
  itAdminColumnHelper.accessor('asset_id', {
    header: 'GADGET',
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
  itAdminColumnHelper.accessor('category', {
    header: 'CATEGORY',
    cell: (info) => {
      const cat = info.getValue() as IssueCategory
      return (
        <Badge variant={IssueCategoryVariants[cat]}>
          {IssueCategoryLabels[cat]}
        </Badge>
      )
    },
  }),
  itAdminColumnHelper.accessor('issue_description', {
    header: 'DESCRIPTION',
    cell: (info) => (
      <span className="text-sm text-muted-foreground line-clamp-1">
        {info.getValue()}
      </span>
    ),
  }),
  itAdminColumnHelper.accessor('status', {
    header: 'STATUS',
    cell: (info) => <IssueStatusBadge status={info.getValue()} />,
  }),
  itAdminColumnHelper.accessor('reported_by', {
    header: 'REPORTED BY',
    cell: (info) => (
      <span className="text-sm font-medium">{info.getValue()}</span>
    ),
  }),
  itAdminColumnHelper.accessor('created_at', {
    header: 'DATE SUBMITTED',
    cell: (info) => (
      <span className="text-sm text-muted-foreground">
        {formatDate(info.getValue()) || '—'}
      </span>
    ),
  }),
  itAdminColumnHelper.accessor('resolved_at', {
    header: 'RESOLVED AT',
    cell: (info) => (
      <span className="text-sm text-muted-foreground">
        {formatDate(info.getValue()) || '—'}
      </span>
    ),
  }),
  itAdminColumnHelper.display({
    id: 'actions',
    header: '',
    cell: ({ row }) => (
      <div className="flex items-center justify-end">
        <Button size="icon" variant="ghost" asChild>
          <Link
            to="/assets/$asset_id/issues/$issue_id"
            params={{
              asset_id: row.original.asset_id,
              issue_id: row.original.issue_id,
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

// ── Employee issue columns (no "reported by", adds resolved_by) ───────────────

const employeeIssueColumns: ColumnDef<AllIssueListItem, any>[] = [
  itAdminColumnHelper.accessor('issue_id', {
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
  itAdminColumnHelper.accessor('asset_id', {
    header: 'GADGET',
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
  itAdminColumnHelper.accessor('category', {
    header: 'CATEGORY',
    cell: (info) => {
      const cat = info.getValue() as IssueCategory
      return (
        <Badge variant={IssueCategoryVariants[cat]}>
          {IssueCategoryLabels[cat]}
        </Badge>
      )
    },
  }),
  itAdminColumnHelper.accessor('issue_description', {
    header: 'DESCRIPTION',
    cell: (info) => (
      <span className="text-sm text-muted-foreground line-clamp-1">
        {info.getValue()}
      </span>
    ),
  }),
  itAdminColumnHelper.accessor('status', {
    header: 'STATUS',
    cell: (info) => <IssueStatusBadge status={info.getValue()} />,
  }),
  itAdminColumnHelper.accessor('created_at', {
    header: 'DATE SUBMITTED',
    cell: (info) => (
      <span className="text-sm text-muted-foreground">
        {formatDate(info.getValue()) || '—'}
      </span>
    ),
  }),
  itAdminColumnHelper.accessor('resolved_by', {
    header: 'RESOLVED BY',
    cell: (info) => (
      <span className="text-sm font-medium">{info.getValue() || '—'}</span>
    ),
  }),
  itAdminColumnHelper.accessor('resolved_at', {
    header: 'RESOLVED AT',
    cell: (info) => (
      <span className="text-sm text-muted-foreground">
        {formatDate(info.getValue()) || '—'}
      </span>
    ),
  }),
  itAdminColumnHelper.display({
    id: 'actions',
    header: '',
    cell: ({ row }) => (
      <div className="flex items-center justify-end">
        <Button size="icon" variant="ghost" asChild>
          <Link
            to="/assets/$asset_id/issues/$issue_id"
            params={{
              asset_id: row.original.asset_id,
              issue_id: row.original.issue_id,
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

// ── Software request columns ──────────────────────────────────────────────────

const softwareColumns: ColumnDef<SoftwareRequestListItem, any>[] = [
  softwareColumnHelper.accessor('software_request_id', {
    header: 'REQUEST ID',
    cell: (info) => (
      <Link
        to="/assets/$asset_id/software-requests/$software_request_id"
        params={{
          asset_id: info.row.original.asset_id,
          software_request_id: info.getValue(),
        }}
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
    header: 'SOFTWARE',
    cell: (info) => (
      <div>
        <p className="text-sm font-medium">{info.getValue()}</p>
        <p className="text-xs text-muted-foreground">
          v{info.row.original.version}
        </p>
      </div>
    ),
  }),
  softwareColumnHelper.accessor('vendor', {
    header: 'VENDOR',
    cell: (info) => (
      <span className="text-sm font-medium">{info.getValue()}</span>
    ),
  }),
  softwareColumnHelper.accessor('license_type', {
    header: 'LICENSE',
    cell: (info) => (
      <span className="text-sm text-muted-foreground">{info.getValue()}</span>
    ),
  }),
  softwareColumnHelper.accessor('data_access_impact', {
    header: 'DATA IMPACT',
    cell: (info) => {
      const val = info.getValue() as string
      return (
        <RiskLevelBadge value={(val as 'LOW' | 'MEDIUM' | 'HIGH') ?? null} />
      )
    },
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
      <span className="text-sm text-muted-foreground">
        {formatDate(info.getValue()) || '—'}
      </span>
    ),
  }),
  softwareColumnHelper.accessor('reviewed_at', {
    header: 'REVIEWED AT',
    cell: (info) => (
      <span className="text-sm text-muted-foreground">
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
            to="/assets/$asset_id/software-requests/$software_request_id"
            params={{
              asset_id: info.row.original.asset_id,
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
]

// ── Employee software columns (no "requested by") ─────────────────────────────

const employeeSoftwareColumns: ColumnDef<SoftwareRequestListItem, any>[] = [
  softwareColumnHelper.accessor('software_request_id', {
    header: 'REQUEST ID',
    cell: (info) => (
      <Link
        to="/assets/$asset_id/software-requests/$software_request_id"
        params={{
          asset_id: info.row.original.asset_id,
          software_request_id: info.getValue(),
        }}
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
    header: 'SOFTWARE',
    cell: (info) => (
      <div>
        <p className="text-sm font-medium">{info.getValue()}</p>
        <p className="text-xs text-muted-foreground">
          v{info.row.original.version}
        </p>
      </div>
    ),
  }),
  softwareColumnHelper.accessor('vendor', {
    header: 'VENDOR',
    cell: (info) => (
      <span className="text-sm font-medium">{info.getValue()}</span>
    ),
  }),
  softwareColumnHelper.accessor('license_type', {
    header: 'LICENSE',
    cell: (info) => (
      <span className="text-sm text-muted-foreground">{info.getValue()}</span>
    ),
  }),
  softwareColumnHelper.accessor('data_access_impact', {
    header: 'DATA IMPACT',
    cell: (info) => {
      const val = info.getValue() as string
      return (
        <RiskLevelBadge value={(val as 'LOW' | 'MEDIUM' | 'HIGH') ?? null} />
      )
    },
  }),
  softwareColumnHelper.accessor('status', {
    header: 'STATUS',
    cell: (info) => <SoftwareStatusBadge status={info.getValue()} />,
  }),
  softwareColumnHelper.accessor('risk_level', {
    header: 'RISK LEVEL',
    cell: (info) => <RiskLevelBadge value={info.getValue() ?? null} />,
  }),
  softwareColumnHelper.accessor('created_at', {
    header: 'CREATED AT',
    cell: (info) => (
      <span className="text-sm text-muted-foreground">
        {formatDate(info.getValue()) || '—'}
      </span>
    ),
  }),
  softwareColumnHelper.accessor('reviewed_by', {
    header: 'REVIEWED BY',
    cell: (info) => (
      <span className="text-sm font-medium">{info.getValue() || '—'}</span>
    ),
  }),
  softwareColumnHelper.accessor('reviewed_at', {
    header: 'REVIEWED AT',
    cell: (info) => (
      <span className="text-sm text-muted-foreground">
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
            to="/assets/$asset_id/software-requests/$software_request_id"
            params={{
              asset_id: info.row.original.asset_id,
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
]

// ── Disposal columns ──────────────────────────────────────────────────────────

const disposalColumnHelper = createColumnHelper<DisposalListItem>()

const disposalColumns: ColumnDef<DisposalListItem, any>[] = [
  disposalColumnHelper.accessor('disposal_id', {
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
  disposalColumnHelper.accessor('asset_id', {
    header: 'ASSET ID',
    cell: (info) => (
      <Link
        to={'/assets/$asset_id/disposals/$disposal_id' as any}
        params={
          {
            asset_id: info.getValue(),
            disposal_id: info.row.original.disposal_id,
          } as any
        }
        className="text-sm font-medium text-info hover:underline"
      >
        {info.getValue()}
      </Link>
    ),
  }),
  disposalColumnHelper.accessor('disposal_reason', {
    header: 'REASON',
    cell: (info) => (
      <span className="text-sm font-medium">{info.getValue()}</span>
    ),
  }),
  disposalColumnHelper.accessor('justification', {
    header: 'JUSTIFICATION',
    cell: (info) => (
      <span
        className="text-sm text-muted-foreground truncate max-w-[200px] block"
        title={info.getValue()}
      >
        {info.getValue()}
      </span>
    ),
  }),
  disposalColumnHelper.accessor('status', {
    header: 'STATUS',
    cell: (info) => <DisposalStatusBadge status={info.getValue()} />,
  }),
  disposalColumnHelper.accessor('initiated_by', {
    header: 'INITIATED BY',
    cell: (info) => (
      <div>
        <p className="text-sm font-medium">{info.getValue()}</p>
        <p className="text-xs text-muted-foreground">
          {formatDate(info.row.original.initiated_at) || '—'}
        </p>
      </div>
    ),
  }),
  disposalColumnHelper.accessor('management_reviewed_by', {
    header: 'REVIEWED BY',
    cell: (info) => {
      const reviewer = info.getValue()
      if (!reviewer)
        return <span className="text-sm text-muted-foreground">—</span>
      return (
        <div>
          <p className="text-sm font-medium">{reviewer}</p>
          <p className="text-xs text-muted-foreground">
            {formatDate(info.row.original.management_reviewed_at) || '—'}
          </p>
        </div>
      )
    },
  }),
  disposalColumnHelper.accessor('data_wipe_confirmed', {
    header: 'DATA WIPED',
    cell: (info) => {
      const val = info.getValue()
      if (val === true) return <Badge variant="success">Yes</Badge>
      if (val === false) return <Badge variant="danger">No</Badge>
      return <span className="text-sm text-muted-foreground">—</span>
    },
  }),
  disposalColumnHelper.accessor('disposal_date', {
    header: 'DISPOSAL DATE',
    cell: (info) => (
      <span className="text-sm text-muted-foreground">
        {info.getValue() ? formatDate(info.getValue()) : '—'}
      </span>
    ),
  }),
  disposalColumnHelper.display({
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
]

// ── Tabs Definition ───────────────────────────────────────────────────────────

const ALL_TABS: TabDef[] = [
  {
    value: 'issues',
    label: 'Issues',
    roles: ['it-admin', 'management', 'employee'],
  },
  {
    value: 'software',
    label: 'Software Installation',
    roles: ['it-admin', 'management', 'employee'],
  },
  { value: 'returns', label: 'Returns', roles: ['it-admin', 'management'] },
  { value: 'disposals', label: 'Disposals', roles: ['it-admin', 'management'] },
]

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

// ── Software Requests Tab Content ─────────────────────────────────────────────

function SoftwareRequestsTabContent({
  history,
  variant = 'admin',
}: {
  history: boolean
  variant?: 'admin' | 'employee'
}) {
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
    (updates: Partial<z.infer<typeof maintenanceSearchSchema>>) => {
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
      history,
    }),
    [
      search.status,
      search.risk_level,
      search.software_name,
      search.vendor,
      search.license_validity_period,
      search.data_access_impact,
      history,
    ],
  )

  const { data, isLoading, error } = useAllSoftwareRequests(
    filters,
    currentCursor,
    pageSize,
  )

  const setSearchAndResetPage = useCallback(
    (updates: Partial<z.infer<typeof maintenanceSearchSchema>>) => {
      onSearchChange({ ...updates })
    },
    [onSearchChange],
  )

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
        columns={
          variant === 'employee' ? employeeSoftwareColumns : softwareColumns
        }
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

// ── Returns columns (module scope) ────────────────────────────────────────────

const allReturnsColumns: ColumnDef<AllReturnListItem, any>[] = [
  allReturnsColumnHelper.accessor('return_id', {
    header: 'RETURN ID',
    cell: (info) => (
      <Link
        to={'/assets/$asset_id/returns/$return_id' as any}
        params={
          {
            asset_id: info.row.original.asset_id,
            return_id: info.getValue(),
          } as any
        }
        className="text-sm font-medium text-info hover:underline"
      >
        {info.getValue()}
      </Link>
    ),
  }),
  allReturnsColumnHelper.accessor('asset_id', {
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
  allReturnsColumnHelper.accessor('model', {
    header: 'MODEL',
    cell: (info) => (
      <span className="text-sm font-medium">{info.getValue() || '—'}</span>
    ),
  }),
  allReturnsColumnHelper.accessor('return_trigger', {
    header: 'TRIGGER',
    cell: (info) => {
      const trigger = info.getValue() as ReturnTrigger
      return (
        <span className="text-sm font-medium">
          {ReturnTriggerLabels[trigger] ?? trigger}
        </span>
      )
    },
  }),
  allReturnsColumnHelper.accessor('condition_assessment', {
    header: 'CONDITION',
    cell: (info) => <ReturnConditionBadge condition={info.getValue()} />,
  }),
  allReturnsColumnHelper.accessor('reset_status', {
    header: 'RESET',
    cell: (info) => <ResetStatusBadge status={info.getValue()} />,
  }),
  allReturnsColumnHelper.accessor('initiated_by', {
    header: 'INITIATED BY',
    cell: (info) => (
      <div>
        <p className="text-sm font-medium">{info.getValue()}</p>
        <p className="text-xs text-muted-foreground">
          {formatDate(info.row.original.initiated_at) || '—'}
        </p>
      </div>
    ),
  }),
  allReturnsColumnHelper.accessor('resolved_status', {
    header: 'STATUS',
    cell: (info) => <ReturnStatusBadge status={info.getValue()} />,
  }),
  allReturnsColumnHelper.accessor('completed_by', {
    header: 'COMPLETED BY',
    cell: (info) => {
      const name = info.getValue()
      if (!name) return <span className="text-sm text-muted-foreground">—</span>
      return (
        <div>
          <p className="text-sm font-medium">{name}</p>
          <p className="text-xs text-muted-foreground">
            {formatDate(info.row.original.completed_at) || '—'}
          </p>
        </div>
      )
    },
  }),
  allReturnsColumnHelper.display({
    id: 'actions',
    header: '',
    cell: ({ row }) => (
      <div className="flex items-center justify-end">
        <Button size="icon" variant="ghost" asChild>
          <Link
            to={'/assets/$asset_id/returns/$return_id' as any}
            params={
              {
                asset_id: row.original.asset_id,
                return_id: row.original.return_id,
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
]

// ── Returns Tab Content ───────────────────────────────────────────────────────

function ReturnsTabContent({ history }: { history: boolean }) {
  const {
    currentCursor,
    goToNextPage,
    goToPreviousPage,
    canGoPrevious,
    pageSize,
  } = useCursorPagination(PAGE_SIZE)

  const filters: ListAllReturnsFilter = useMemo(
    () => ({
      history,
    }),
    [history],
  )

  const { data, isLoading, error } = useAllReturns(
    filters,
    currentCursor,
    pageSize,
  )

  const tableData = useMemo(() => data?.items ?? [], [data])

  return (
    <DataTable
      columns={allReturnsColumns}
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
  )
}

// ── Disposal filter dialog state ──────────────────────────────────────────────

type DisposalDialogFilterState = {
  status: DisposalStatus | 'all'
  disposal_reason: string
  date_from: string
  date_to: string
}

const EMPTY_DISPOSAL_FILTERS: DisposalDialogFilterState = {
  status: 'all',
  disposal_reason: '',
  date_from: '',
  date_to: '',
}

// ── Disposal Filter Dialog ────────────────────────────────────────────────────

function DisposalFilterDialog({
  open,
  onOpenChange,
  current,
  onApply,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  current: DisposalDialogFilterState
  onApply: (filters: DisposalDialogFilterState) => void
}) {
  const [draft, setDraft] = useState<DisposalDialogFilterState>(current)
  const [dateFromOpen, setDateFromOpen] = useState(false)
  const [dateToOpen, setDateToOpen] = useState(false)

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
            Narrow down the disposal list by status, reason, or date range.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 overflow-y-auto -mx-1 px-1">
          <div className="space-y-1.5">
            <Label htmlFor="filter-disposal-status">Status</Label>
            <Select
              value={draft.status}
              onValueChange={(v) =>
                setDraft((d) => ({ ...d, status: v as DisposalStatus | 'all' }))
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

          <div className="space-y-1.5">
            <Label htmlFor="filter-disposal-reason">Disposal Reason</Label>
            <Input
              id="filter-disposal-reason"
              placeholder="e.g. End of life"
              value={draft.disposal_reason}
              onChange={(e) =>
                setDraft((d) => ({ ...d, disposal_reason: e.target.value }))
              }
            />
          </div>

          <div className="space-y-1.5">
            <Label>Date From</Label>
            <Popover open={dateFromOpen} onOpenChange={setDateFromOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn(
                    'w-full justify-start text-left font-normal',
                    !draft.date_from && 'text-muted-foreground',
                  )}
                >
                  <CalendarIcon className="size-4" />
                  {draft.date_from
                    ? formatDate(draft.date_from)
                    : 'Pick a date'}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={
                    draft.date_from ? new Date(draft.date_from) : undefined
                  }
                  onSelect={(date) => {
                    setDraft((d) => ({
                      ...d,
                      date_from: date ? format(date, 'yyyy-MM-dd') : '',
                    }))
                    setDateFromOpen(false)
                  }}
                  autoFocus
                />
              </PopoverContent>
            </Popover>
          </div>

          <div className="space-y-1.5">
            <Label>Date To</Label>
            <Popover open={dateToOpen} onOpenChange={setDateToOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn(
                    'w-full justify-start text-left font-normal',
                    !draft.date_to && 'text-muted-foreground',
                  )}
                >
                  <CalendarIcon className="size-4" />
                  {draft.date_to ? formatDate(draft.date_to) : 'Pick a date'}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={draft.date_to ? new Date(draft.date_to) : undefined}
                  onSelect={(date) => {
                    setDraft((d) => ({
                      ...d,
                      date_to: date ? format(date, 'yyyy-MM-dd') : '',
                    }))
                    setDateToOpen(false)
                  }}
                  autoFocus
                />
              </PopoverContent>
            </Popover>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => setDraft(EMPTY_DISPOSAL_FILTERS)}
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

// ── Disposals Tab Content ─────────────────────────────────────────────────────
function DisposalsTabContent({ history }: { history: boolean }) {
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
    (updates: Partial<z.infer<typeof maintenanceSearchSchema>>) => {
      resetPagination()
      void navigate({
        to: '.',
        search: (prev: Record<string, unknown>) => ({ ...prev, ...updates }) as any,
        replace: true,
      })
    },
    [navigate, resetPagination],
  )

  const filters: ListDisposalsFilter = useMemo(
    () => ({
      ...(search.disposal_status && { status: search.disposal_status }),
      ...(search.disposal_reason && {
        disposal_reason: search.disposal_reason,
      }),
      ...(search.date_from && { date_from: search.date_from }),
      ...(search.date_to && { date_to: search.date_to }),
      history,
    }),
    [
      search.disposal_status,
      search.disposal_reason,
      search.date_from,
      search.date_to,
      history,
    ],
  )

  const { data, isLoading, error } = useDisposals(
    filters,
    currentCursor,
    pageSize,
  )

  const dialogFilters: DisposalDialogFilterState = useMemo(
    () => ({
      status: search.disposal_status ?? 'all',
      disposal_reason: search.disposal_reason ?? '',
      date_from: search.date_from ?? '',
      date_to: search.date_to ?? '',
    }),
    [
      search.disposal_status,
      search.disposal_reason,
      search.date_from,
      search.date_to,
    ],
  )

  const handleApplyDialogFilters = useCallback(
    (f: DisposalDialogFilterState) => {
      onSearchChange({
        disposal_status:
          f.status === 'all' ? undefined : (f.status as DisposalStatus),
        disposal_reason: f.disposal_reason || undefined,
        date_from: f.date_from || undefined,
        date_to: f.date_to || undefined,
      })
    },
    [onSearchChange],
  )

  const dialogFilterCount = [
    search.disposal_status,
    search.disposal_reason,
    search.date_from,
    search.date_to,
  ].filter(Boolean).length
  const hasAnyFilter = dialogFilterCount > 0

  const clearAllFilters = useCallback(() => {
    onSearchChange({
      disposal_status: undefined,
      disposal_reason: undefined,
      date_from: undefined,
      date_to: undefined,
    })
  }, [onSearchChange])

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
        columns={disposalColumns}
        data={tableData}
        entityName="disposal records"
        isLoading={isLoading}
        error={error ? (error as Error).message : undefined}
        pageSize={pageSize}
        hasNextPage={data?.has_next_page ?? false}
        canGoPrevious={canGoPrevious}
        onNextPage={() => data?.next_cursor && goToNextPage(data.next_cursor)}
        onPreviousPage={goToPreviousPage}
      />

      <DisposalFilterDialog
        open={filterOpen}
        onOpenChange={setFilterOpen}
        current={dialogFilters}
        onApply={handleApplyDialogFilters}
      />
    </>
  )
}

// ── Issue filter state ────────────────────────────────────────────────────────

type IssueFilterState = {
  status: IssueStatus | 'all'
  category: IssueCategory | 'all'
  sort_order: SortOrder
}

const EMPTY_ISSUE_FILTERS: IssueFilterState = {
  status: 'all',
  category: 'all',
  sort_order: 'desc',
}

function IssueFilterDialog({
  open,
  onOpenChange,
  current,
  onApply,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  current: IssueFilterState
  onApply: (f: IssueFilterState) => void
}) {
  const [draft, setDraft] = useState<IssueFilterState>(current)

  const handleOpenChange = (next: boolean) => {
    if (next) setDraft(current)
    onOpenChange(next)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Filter Issues</DialogTitle>
          <DialogDescription>
            Narrow down issues by status, category, or sort order.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 -mx-1 px-1">
          <div className="space-y-1.5">
            <Label htmlFor="filter-issue-status">Status</Label>
            <Select
              value={draft.status}
              onValueChange={(v) =>
                setDraft((d) => ({ ...d, status: v as IssueStatus | 'all' }))
              }
            >
              <SelectTrigger id="filter-issue-status" className="w-full">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                {(Object.keys(IssueStatusLabels) as IssueStatus[]).map((s) => (
                  <SelectItem key={s} value={s}>
                    {IssueStatusLabels[s]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="filter-issue-category">Category</Label>
            <Select
              value={draft.category}
              onValueChange={(v) =>
                setDraft((d) => ({
                  ...d,
                  category: v as IssueCategory | 'all',
                }))
              }
            >
              <SelectTrigger id="filter-issue-category" className="w-full">
                <SelectValue placeholder="All Categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {(Object.keys(IssueCategoryLabels) as IssueCategory[]).map(
                  (c) => (
                    <SelectItem key={c} value={c}>
                      {IssueCategoryLabels[c]}
                    </SelectItem>
                  ),
                )}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="filter-issue-sort-order">Sort Order</Label>
            <Select
              value={draft.sort_order}
              onValueChange={(v) =>
                setDraft((d) => ({ ...d, sort_order: v as SortOrder }))
              }
            >
              <SelectTrigger id="filter-issue-sort-order" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="desc">Newest First</SelectItem>
                <SelectItem value="asc">Oldest First</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setDraft(EMPTY_ISSUE_FILTERS)}>
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

// ── Issues Tab Content ────────────────────────────────────────────────────────

function IssuesTabContent({
  history,
  variant = 'admin',
}: {
  history: boolean
  variant?: 'admin' | 'employee'
}) {
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
    (updates: Partial<z.infer<typeof maintenanceSearchSchema>>) => {
      resetPagination()
      void navigate({
        to: '.',
        search: (prev: Record<string, unknown>) => ({ ...prev, ...updates }) as any,
        replace: true,
      })
    },
    [navigate, resetPagination],
  )

  const issueFilters: ListAllIssuesFilter = useMemo(
    () => ({
      ...(search.issue_status && { status: search.issue_status }),
      ...(search.issue_category && { category: search.issue_category }),
      sort_order: search.issue_sort_order ?? 'desc',
      history,
    }),
    [
      search.issue_status,
      search.issue_category,
      search.issue_sort_order,
      history,
    ],
  )

  const { data, isLoading, error } = useAllIssues(
    issueFilters,
    currentCursor,
    pageSize,
  )

  const tableData = useMemo(() => data?.items ?? [], [data])

  const currentFilters: IssueFilterState = useMemo(
    () => ({
      status: search.issue_status ?? 'all',
      category: search.issue_category ?? 'all',
      sort_order: search.issue_sort_order ?? 'desc',
    }),
    [search.issue_status, search.issue_category, search.issue_sort_order],
  )

  const handleApply = useCallback(
    (f: IssueFilterState) => {
      onSearchChange({
        issue_status: f.status === 'all' ? undefined : f.status,
        issue_category: f.category === 'all' ? undefined : f.category,
        issue_sort_order: f.sort_order === 'desc' ? undefined : f.sort_order,
      })
    },
    [onSearchChange],
  )

  const dialogFilterCount = [
    search.issue_status,
    search.issue_category,
    search.issue_sort_order && search.issue_sort_order !== 'desc'
      ? search.issue_sort_order
      : undefined,
  ].filter(Boolean).length

  const hasAnyFilter = dialogFilterCount > 0

  const clearAllFilters = useCallback(() => {
    onSearchChange({
      issue_status: undefined,
      issue_category: undefined,
      issue_sort_order: undefined,
    })
  }, [onSearchChange])

  return (
    <>
      {error && <div className="alert-danger">{(error as Error).message}</div>}
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
        columns={variant === 'employee' ? employeeIssueColumns : itAdminColumns}
        data={tableData}
        entityName="issues"
        isLoading={isLoading}
        pageSize={pageSize}
        hasNextPage={data?.has_next_page ?? false}
        canGoPrevious={canGoPrevious}
        onNextPage={() => data?.next_cursor && goToNextPage(data.next_cursor)}
        onPreviousPage={goToPreviousPage}
      />
      <IssueFilterDialog
        open={filterOpen}
        onOpenChange={setFilterOpen}
        current={currentFilters}
        onApply={handleApply}
      />
    </>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

function MaintenancePage() {
  const role = useCurrentUserRole()
  if (hasRole(role, ['it-admin', 'management'])) return <AdminManagementView />
  return <EmployeeView />
}

// ── Admin / Management View ───────────────────────────────────────────────────

function AdminManagementView() {
  const navigate = useNavigate()
  const search = Route.useSearch()
  const role = useCurrentUserRole()
  const { data: reqStats, isLoading: reqStatsLoading } =
    useRequestsITAdminStats()

  const showHistory = search.history ?? false

  const visibleTabs = useMemo(
    () => ALL_TABS.filter((t) => role && t.roles.includes(role)),
    [role],
  )

  const defaultTab = visibleTabs[0]?.value ?? 'issues'
  const activeTab =
    search.tab && visibleTabs.some((t) => t.value === search.tab)
      ? search.tab
      : defaultTab

  const handleTabChange = useCallback(
    (tab: string) => {
      void navigate({
        to: '/requests',
        search: { tab: tab as any, history: search.history },
        replace: true,
      })
    },
    [navigate, search.history],
  )

  const handleHistoryToggle = useCallback(
    (checked: boolean) => {
      void navigate({
        to: '/requests',
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
          <h1 className="page-title">Requests Hub</h1>
          <p className="page-subtitle">
            Manage assets tickets & issues requests.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Label
            htmlFor="history-toggle"
            className="text-sm text-muted-foreground"
          >
            Show History
          </Label>
          <Switch
            id="history-toggle"
            checked={showHistory}
            onCheckedChange={handleHistoryToggle}
          />
        </div>
      </div>

      {hasRole(role, ['it-admin']) && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4">
          <StatCard
            loading={reqStatsLoading}
            title="Completed Today"
            data={formatNumber(reqStats?.completed_today ?? 0)}
            Icon={CheckCircle2Icon}
          />
          <StatCard
            loading={reqStatsLoading}
            title="Total Active Requests"
            data={formatNumber(reqStats?.total_active_requests ?? 0)}
            Icon={CheckCircle2}
          />
          <StatCard
            loading={reqStatsLoading}
            title="Pending Returns"
            data={formatNumber(reqStats?.pending_returns ?? 0)}
            Icon={CalendarCheck2}
          />
        </div>
      )}

      <Tabs value={activeTab} onValueChange={handleTabChange} className="mt-4">
        <TabsList variant="line">
          {visibleTabs.map((item) => (
            <TabsTrigger key={item.value} value={item.value}>
              {item.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="issues" className="space-y-4 mt-4">
          <IssuesTabContent history={showHistory} />
        </TabsContent>

        <TabsContent value="software" className="space-y-4 mt-4">
          <SoftwareRequestsTabContent history={showHistory} />
        </TabsContent>

        <TabsContent value="returns" className="space-y-4 mt-4">
          <ReturnsTabContent history={showHistory} />
        </TabsContent>

        <TabsContent value="disposals" className="space-y-4 mt-4">
          <DisposalsTabContent history={showHistory} />
        </TabsContent>
      </Tabs>
    </main>
  )
}

// ── Employee View ─────────────────────────────────────────────────────────────

function EmployeeView() {
  const navigate = useNavigate({ from: '/requests' })
  const matchRoute = useMatchRoute()
  const search = Route.useSearch()
  const { data: empStats, isLoading: empStatsLoading } =
    useRequestsEmployeeStats()

  const showHistory = search.history ?? false

  const visibleTabs = useMemo(
    () => ALL_TABS.filter((t) => t.roles.includes('employee')),
    [],
  )

  const defaultTab = visibleTabs[0]?.value ?? 'issues'
  const activeTab =
    search.tab && visibleTabs.some((t) => t.value === search.tab)
      ? search.tab
      : defaultTab

  // All hooks above — safe to early-return for child routes now
  const isChildRouteActive =
    matchRoute({ to: '/requests/new-issue', fuzzy: true }) ||
    matchRoute({ to: '/requests/new-software', fuzzy: true })
  if (isChildRouteActive) {
    return <Outlet />
  }

  function handleTabChange(value: string) {
    void navigate({
      search: { tab: value as any, history: search.history },
    })
  }

  function handleHistoryToggle(checked: boolean) {
    void navigate({
      search: (prev: Record<string, unknown>) =>
        ({ ...prev, history: checked || undefined }) as any,
    })
  }

  return (
    <main className="page-base">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Requests</h1>
          <p className="text-muted-foreground mt-1">
            Track and manage your hardware applications and reported issues.
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Label
              htmlFor="emp-history-toggle"
              className="text-sm text-muted-foreground"
            >
              Show History
            </Label>
            <Switch
              id="emp-history-toggle"
              checked={showHistory}
              onCheckedChange={handleHistoryToggle}
            />
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link to="/requests/new-software">Request Software</Link>
            </Button>
            <Button variant="default" size="sm" asChild>
              <Link to="/requests/new-issue">Report Issue</Link>
            </Button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6">
        <StatCard
          loading={empStatsLoading}
          title="Active Requests"
          data={formatNumber(empStats?.active_requests ?? 0)}
          Icon={ClipboardList}
        />
        <StatCard
          loading={empStatsLoading}
          title="Pending Approval"
          data={formatNumber(empStats?.pending_approval ?? 0)}
          Icon={AlertTriangle}
        />
        <StatCard
          loading={empStatsLoading}
          title="Resolved (Monthly)"
          data={formatNumber(empStats?.resolved_monthly ?? 0)}
          Icon={CheckCircle}
        />
      </div>

      <Tabs value={activeTab} onValueChange={handleTabChange} className="mt-6">
        <TabsList variant="line">
          {visibleTabs.map((t) => (
            <TabsTrigger key={t.value} value={t.value}>
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="issues" className="space-y-4 mt-4">
          <IssuesTabContent history={showHistory} variant="employee" />
        </TabsContent>

        <TabsContent value="software" className="space-y-4 mt-4">
          <SoftwareRequestsTabContent
            history={showHistory}
            variant="employee"
          />
        </TabsContent>
      </Tabs>
    </main>
  )
}
