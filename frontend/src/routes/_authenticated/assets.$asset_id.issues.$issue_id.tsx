import { lazy, Suspense, useState } from 'react'
import { createFileRoute, redirect, Link } from '@tanstack/react-router'
import {
  AlertTriangle,
  Camera,
  Calendar,
  CheckCircle2,
  Clock,
  FileText,
  Hammer,
  RefreshCw,
  Shield,
  User,
  Wrench,
} from 'lucide-react'
import type { UserRole } from '#/lib/models/types'
import {
  getBaseMeta,
  getPageMeta,
  getCanonicalLink,
  type SeoPageInput,
} from '../../lib/seo'
import { useIssueDetail } from '#/hooks/use-issues'
import { useCurrentUserRole } from '#/hooks/use-current-user'
import { getIssueActionPermissions, hasRole } from '#/lib/permissions'
import { IssueCategoryLabels } from '#/lib/models/labels'
import { formatDate } from '#/lib/utils'
import { Skeleton } from '#/components/ui/skeleton'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'
import { Card, CardHeader, CardTitle, CardContent } from '#/components/ui/card'
import { Separator } from '#/components/ui/separator'
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbSeparator,
  BreadcrumbPage,
} from '#/components/ui/breadcrumb'
import { IssueStatusBadge } from '#/components/issues/IssueStatusBadge'
import type { IssueCategory } from '#/lib/models/types'

// Lazy-loaded dialogs
const StartRepairDialog = lazy(() =>
  import('#/components/issues/StartRepairDialog').then((m) => ({
    default: m.StartRepairDialog,
  })),
)
const SendWarrantyDialog = lazy(() =>
  import('#/components/issues/SendWarrantyDialog').then((m) => ({
    default: m.SendWarrantyDialog,
  })),
)
const CompleteRepairDialog = lazy(() =>
  import('#/components/issues/CompleteRepairDialog').then((m) => ({
    default: m.CompleteRepairDialog,
  })),
)
const RequestReplacementDialog = lazy(() =>
  import('#/components/issues/RequestReplacementDialog').then((m) => ({
    default: m.RequestReplacementDialog,
  })),
)
const ManagementReviewIssueDialog = lazy(() =>
  import('#/components/issues/ManagementReviewIssueDialog').then((m) => ({
    default: m.ManagementReviewIssueDialog,
  })),
)

// ── SEO ───────────────────────────────────────────────────────────────────────

const ISSUE_DETAIL_SEO = {
  title: 'Issue Detail',
  description:
    'View full issue details including status, triage information, repair progress, and management review decisions.',
  path: '/assets/issues/detail',
} satisfies SeoPageInput

// ── Route config ──────────────────────────────────────────────────────────────

const ALLOWED: UserRole[] = ['it-admin', 'management', 'employee']

export const Route = createFileRoute(
  '/_authenticated/assets/$asset_id/issues/$issue_id' as any,
)({
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
  component: IssueDetailPage,
  head: () => ({
    meta: [
      ...getBaseMeta(),
      { name: 'robots', content: 'noindex, nofollow' },
      ...getPageMeta(ISSUE_DETAIL_SEO),
    ],
    links: [getCanonicalLink(ISSUE_DETAIL_SEO.path)],
  }),
})

// ── Component ─────────────────────────────────────────────────────────────────

function IssueDetailPage() {
  const { asset_id, issue_id } = Route.useParams() as {
    asset_id: string
    issue_id: string
  }
  const role = useCurrentUserRole()
  const { data: issue, isLoading, error } = useIssueDetail(asset_id, issue_id)

  const [startRepairOpen, setStartRepairOpen] = useState(false)
  const [sendWarrantyOpen, setSendWarrantyOpen] = useState(false)
  const [completeRepairOpen, setCompleteRepairOpen] = useState(false)
  const [requestReplacementOpen, setRequestReplacementOpen] = useState(false)
  const [managementReviewOpen, setManagementReviewOpen] = useState(false)

  const actions = issue
    ? getIssueActionPermissions({ role, issueStatus: issue.status })
    : null

  return (
    <main className="page-base">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link to="/assets">Assets</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link to="/assets/$asset_id" params={{ asset_id }}>
                {asset_id}
              </Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>Issue Detail</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      {isLoading && <IssueDetailSkeleton />}

      {error && (
        <div className="alert-danger mt-4">{(error as Error).message}</div>
      )}

      {issue && (
        <div className="mt-4 space-y-6">
          {/* Hero Card */}
          <Card>
            <CardContent className="flex flex-col sm:flex-row sm:items-center gap-4">
              <div className="flex size-14 shrink-0 items-center justify-center rounded-lg bg-danger-subtle">
                <AlertTriangle
                  className="size-7 text-danger"
                  strokeWidth={1.5}
                />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <h1 className="text-xl font-semibold truncate">
                    {issue.issue_description.length > 60
                      ? `${issue.issue_description.slice(0, 60)}…`
                      : issue.issue_description}
                  </h1>
                  <IssueStatusBadge status={issue.status} />
                </div>
                <p className="text-sm text-muted-foreground">
                  Asset{' '}
                  <Link
                    to="/assets/$asset_id"
                    params={{ asset_id }}
                    className="text-info font-medium hover:underline"
                  >
                    {asset_id}
                  </Link>
                  {' · '}
                  <Badge variant="outline" size="sm">
                    {IssueCategoryLabels[issue.category as IssueCategory]}
                  </Badge>
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2 sm:ml-auto shrink-0">
                {actions?.canStartRepair && (
                  <>
                    <Button size="sm" onClick={() => setStartRepairOpen(true)}>
                      <Wrench className="size-4 mr-1.5" />
                      Start Repair
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setRequestReplacementOpen(true)}
                    >
                      <RefreshCw className="size-4 mr-1.5" />
                      Request Replacement
                    </Button>
                  </>
                )}
                {actions?.canSendWarranty && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setSendWarrantyOpen(true)}
                  >
                    <Shield className="size-4 mr-1.5" />
                    Send to Warranty
                  </Button>
                )}
                {actions?.canCompleteRepair && (
                  <Button size="sm" onClick={() => setCompleteRepairOpen(true)}>
                    <CheckCircle2 className="size-4 mr-1.5" />
                    Complete Repair
                  </Button>
                )}
                {actions?.canManagementReview && (
                  <Button
                    size="sm"
                    onClick={() => setManagementReviewOpen(true)}
                  >
                    Review Replacement
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Quick Info Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <QuickInfoCard
              icon={Calendar}
              label="Reported"
              value={formatDate(issue.created_at) || '—'}
            />
            <QuickInfoCard
              icon={User}
              label="Reported By"
              value={issue.reported_by}
            />
            <QuickInfoCard
              icon={Hammer}
              label="Action"
              value={
                issue.action_path === 'REPAIR'
                  ? 'Repair'
                  : issue.action_path === 'REPLACEMENT'
                    ? 'Replacement'
                    : 'Pending'
              }
            />
            <QuickInfoCard
              icon={Clock}
              label="Resolved At"
              value={formatDate(issue.resolved_at) || 'In Progress'}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left column — main content */}
            <div className="lg:col-span-2 space-y-6">
              {/* Description */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">
                    <FileText className="size-4 inline mr-1.5 -mt-0.5" />
                    Description
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-relaxed">
                    {issue.issue_description}
                  </p>
                </CardContent>
              </Card>

              {/* Evidence Photos */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">
                    <Camera className="size-4 inline mr-1.5 -mt-0.5" />
                    Evidence Photos
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {issue.issue_photo_urls &&
                    issue.issue_photo_urls.length > 0 ? (
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                      {issue.issue_photo_urls.map((url, i) => (
                        <a
                          key={i}
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block aspect-square rounded-lg overflow-hidden border hover:ring-2 hover:ring-primary transition-shadow"
                        >
                          <img
                            src={url}
                            alt={`Issue photo ${i + 1}`}
                            className="h-full w-full object-cover"
                          />
                        </a>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      No photos attached.
                    </p>
                  )}
                </CardContent>
              </Card>

              {/* Repair Details */}
              {issue.action_path === 'REPAIR' && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">
                      <Wrench className="size-4 inline mr-1.5 -mt-0.5" />
                      Repair Details
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
                      {issue.repair_notes && (
                        <DetailItem
                          label="Repair Notes"
                          value={issue.repair_notes}
                          fullWidth
                        />
                      )}
                      {issue.warranty_notes && (
                        <DetailItem
                          label="Warranty Notes"
                          value={issue.warranty_notes}
                          fullWidth
                        />
                      )}
                      {issue.warranty_sent_at && (
                        <DetailItem
                          label="Warranty Sent"
                          value={formatDate(issue.warranty_sent_at) || '—'}
                        />
                      )}
                      {issue.resolved_by && (
                        <DetailItem
                          label="Resolved By"
                          value={issue.resolved_by}
                        />
                      )}
                      {issue.resolved_at && (
                        <DetailItem
                          label="Resolved At"
                          value={formatDate(issue.resolved_at) || '—'}
                        />
                      )}
                      {issue.completed_at && (
                        <>
                          <Separator className="sm:col-span-2 my-1" />
                          <DetailItem
                            label="Completed At"
                            value={formatDate(issue.completed_at) || '—'}
                          />
                        </>
                      )}
                      {issue.completion_notes && (
                        <DetailItem
                          label="Completion Notes"
                          value={issue.completion_notes}
                          fullWidth
                        />
                      )}
                    </dl>
                  </CardContent>
                </Card>
              )}

              {/* Replacement Details */}
              {issue.action_path === 'REPLACEMENT' && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">
                      <RefreshCw className="size-4 inline mr-1.5 -mt-0.5" />
                      Replacement Details
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
                      {issue.replacement_justification && (
                        <DetailItem
                          label="Justification"
                          value={issue.replacement_justification}
                          fullWidth
                        />
                      )}
                      {issue.resolved_by && (
                        <DetailItem
                          label="Resolved By"
                          value={issue.resolved_by}
                        />
                      )}
                      {issue.resolved_at && (
                        <DetailItem
                          label="Resolved At"
                          value={formatDate(issue.resolved_at) || '—'}
                        />
                      )}
                    </dl>
                  </CardContent>
                </Card>
              )}
            </div>

            {/* Right sidebar */}
            <div className="space-y-6">
              {/* Timeline / Activity */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">
                    Timeline
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ol className="relative border-s border-border ms-2 space-y-6">
                    <TimelineItem
                      label="Reported"
                      date={formatDate(issue.created_at)}
                      person={issue.reported_by}
                      active
                    />
                    {issue.resolved_by && (
                      <TimelineItem
                        label={
                          issue.action_path === 'REPAIR'
                            ? 'Repair Started'
                            : 'Replacement Requested'
                        }
                        date={formatDate(issue.resolved_at)}
                        person={issue.resolved_by}
                        active
                      />
                    )}
                    {issue.warranty_sent_at && (
                      <TimelineItem
                        label="Sent to Warranty"
                        date={formatDate(issue.warranty_sent_at)}
                        active
                      />
                    )}
                    {issue.management_reviewed_by && (
                      <TimelineItem
                        label="Management Reviewed"
                        date={formatDate(issue.management_reviewed_at)}
                        person={issue.management_reviewed_by}
                        active
                      />
                    )}
                    {issue.completed_at && (
                      <TimelineItem
                        label="Completed"
                        date={formatDate(issue.completed_at)}
                        active
                      />
                    )}
                  </ol>
                </CardContent>
              </Card>

              {/* Management Review */}
              {issue.management_reviewed_by && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">
                      Management Review
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center gap-2 text-sm">
                      <User className="size-4 text-muted-foreground" />
                      <span>{issue.management_reviewed_by}</span>
                    </div>
                    {issue.management_reviewed_at && (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Calendar className="size-4" />
                        <span>{formatDate(issue.management_reviewed_at)}</span>
                      </div>
                    )}
                    {issue.management_remarks && (
                      <div>
                        <p className="text-xs font-semibold text-muted-foreground mb-1">
                          Remarks
                        </p>
                        <p className="text-sm">{issue.management_remarks}</p>
                      </div>
                    )}
                    {issue.management_rejection_reason && (
                      <div>
                        <p className="text-xs font-semibold text-muted-foreground mb-1">
                          Rejection Reason
                        </p>
                        <p className="text-sm text-danger">
                          {issue.management_rejection_reason}
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </div>
          </div>

          {/* Dialogs */}
          <Suspense fallback={null}>
            <StartRepairDialog
              open={startRepairOpen}
              onOpenChange={setStartRepairOpen}
              assetId={asset_id}
              issueId={issue_id}
            />
            <SendWarrantyDialog
              open={sendWarrantyOpen}
              onOpenChange={setSendWarrantyOpen}
              assetId={asset_id}
              issueId={issue_id}
            />
            <CompleteRepairDialog
              open={completeRepairOpen}
              onOpenChange={setCompleteRepairOpen}
              assetId={asset_id}
              issueId={issue_id}
            />
            <RequestReplacementDialog
              open={requestReplacementOpen}
              onOpenChange={setRequestReplacementOpen}
              assetId={asset_id}
              issueId={issue_id}
            />
            <ManagementReviewIssueDialog
              open={managementReviewOpen}
              onOpenChange={setManagementReviewOpen}
              assetId={asset_id}
              issueId={issue_id}
            />
          </Suspense>
        </div>
      )}
    </main>
  )
}

// ── Quick Info Card ───────────────────────────────────────────────────────────

function QuickInfoCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType
  label: string
  value: string
}) {
  return (
    <Card className="gap-3 py-4">
      <CardContent className="flex items-start gap-3">
        <Icon
          className="size-4 mt-0.5 text-muted-foreground"
          strokeWidth={1.5}
        />
        <div className="space-y-0.5">
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-sm font-semibold">{value}</p>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Timeline Item ─────────────────────────────────────────────────────────────

function TimelineItem({
  label,
  date,
  person,
  active,
}: {
  label: string
  date?: string
  person?: string
  active?: boolean
}) {
  return (
    <li className="ms-4">
      <div
        className={`absolute -start-1.5 mt-1 size-3 rounded-full border border-background ${active ? 'bg-primary' : 'bg-muted-foreground'}`}
      />
      <p className="text-sm font-medium">{label}</p>
      {date && <p className="text-xs text-muted-foreground">{date}</p>}
      {person && <p className="text-xs text-muted-foreground">{person}</p>}
    </li>
  )
}

// ── Detail Item ───────────────────────────────────────────────────────────────

function DetailItem({
  label,
  value,
  fullWidth,
}: {
  label: string
  value: string
  fullWidth?: boolean
}) {
  return (
    <div className={fullWidth ? 'sm:col-span-2' : undefined}>
      <dt className="text-xs font-semibold text-muted-foreground mb-1">
        {label}
      </dt>
      <dd className="text-sm">{value}</dd>
    </div>
  )
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function IssueDetailSkeleton() {
  return (
    <div className="mt-4 space-y-6">
      {/* Hero */}
      <Card>
        <CardContent className="flex items-center gap-4">
          <Skeleton className="size-14 rounded-lg" />
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <Skeleton className="h-6 w-64" />
              <Skeleton className="h-5 w-20 rounded-full" />
            </div>
            <Skeleton className="h-4 w-48" />
          </div>
          <div className="flex gap-2">
            <Skeleton className="h-8 w-28" />
            <Skeleton className="h-8 w-36" />
          </div>
        </CardContent>
      </Card>

      {/* Quick Info */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} className="gap-3 py-4">
            <CardContent className="flex items-start gap-3">
              <Skeleton className="size-4 rounded" />
              <div className="space-y-1.5">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-4 w-24" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          <Card>
            <CardHeader>
              <Skeleton className="h-4 w-24" />
            </CardHeader>
            <CardContent className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </CardContent>
          </Card>
          {/* Photos */}
          <Card>
            <CardHeader>
              <Skeleton className="h-4 w-32" />
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="aspect-square rounded-lg" />
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <Skeleton className="h-4 w-20" />
            </CardHeader>
            <CardContent className="space-y-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="flex items-center gap-2">
                  <Skeleton className="size-3 rounded-full" />
                  <div className="space-y-1">
                    <Skeleton className="h-4 w-28" />
                    <Skeleton className="h-3 w-20" />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
