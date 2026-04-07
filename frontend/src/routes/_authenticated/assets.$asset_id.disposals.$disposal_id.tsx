import { lazy, Suspense, useState } from 'react'
import { createFileRoute, redirect, Link } from '@tanstack/react-router'
import { Info, ClipboardCheck, CheckCircle, Bell, Lock } from 'lucide-react'
import { DisposalStatusBadge } from '#/components/disposals/DisposalStatusBadge'

// Lazy-loaded dialogs
const ApproveDisposalDialog = lazy(() =>
  import('#/components/disposals/ApproveDisposalDialog').then((m) => ({
    default: m.ApproveDisposalDialog,
  })),
)
const RejectDisposalDialog = lazy(() =>
  import('#/components/disposals/RejectDisposalDialog').then((m) => ({
    default: m.RejectDisposalDialog,
  })),
)
const CompleteDisposalDialog = lazy(() =>
  import('#/components/disposals/CompleteDisposalDialog').then((m) => ({
    default: m.CompleteDisposalDialog,
  })),
)
import type { UserRole } from '#/lib/models/types'
import {
  getBaseMeta,
  getPageMeta,
  getCanonicalLink,
  type SeoPageInput,
} from '../../lib/seo'
import { useDisposalDetail } from '#/hooks/use-disposals'
import { useCurrentUserRole } from '#/hooks/use-current-user'
import { hasRole, getDisposalDetailPermissions } from '#/lib/permissions'
import { formatDate, formatNumber } from '#/lib/utils'
import { FinanceNotificationStatusLabels } from '#/lib/models/labels'
import { FinanceNotificationStatusVariants } from '#/lib/models/badge-variants'
import { Skeleton } from '#/components/ui/skeleton'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'
import { Card, CardHeader, CardTitle, CardContent } from '#/components/ui/card'
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbSeparator,
  BreadcrumbPage,
} from '#/components/ui/breadcrumb'

// ── SEO ───────────────────────────────────────────────────────────────────────

const DISPOSAL_DETAIL_SEO = {
  title: 'Disposal Detail',
  description:
    'View full disposal record details including asset specs, management review, completion status, and finance notification.',
  path: '/assets/disposals/detail',
} satisfies SeoPageInput

// ── Route config ──────────────────────────────────────────────────────────────

const ALLOWED: UserRole[] = ['it-admin', 'management']

export const Route = createFileRoute(
  '/_authenticated/assets/$asset_id/disposals/$disposal_id' as any,
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
  component: DisposalDetailPage,
  head: () => ({
    meta: [
      ...getBaseMeta(),
      { name: 'robots', content: 'noindex, nofollow' },
      ...getPageMeta(DISPOSAL_DETAIL_SEO),
    ],
    links: [getCanonicalLink(DISPOSAL_DETAIL_SEO.path)],
  }),
})

// ── Component ─────────────────────────────────────────────────────────────────

function DisposalDetailPage() {
  const { asset_id, disposal_id } = Route.useParams() as {
    asset_id: string
    disposal_id: string
  }
  const role = useCurrentUserRole()
  const {
    data: disposal,
    isLoading,
    error,
  } = useDisposalDetail(asset_id, disposal_id)

  // Dialog open states — dialogs will be wired in Tasks 7.3 and 8.3
  const [approveDialogOpen, setApproveDialogOpen] = useState(false)
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false)
  const [completeDialogOpen, setCompleteDialogOpen] = useState(false)

  // Use the status field returned by the API directly
  const permissions = disposal
    ? getDisposalDetailPermissions({
      role,
      assetStatus: disposal.status,
      managementApprovedAt: disposal.management_approved_at,
    })
    : null

  // When locked, hide all actions regardless of permissions
  const isLocked = disposal?.is_locked === true
  const canManagementReview =
    !isLocked && (permissions?.canManagementReview ?? false)
  const canCompleteDisposal =
    !isLocked && (permissions?.canCompleteDisposal ?? false)

  return (
    <main className="page-base">
      {/* Breadcrumb */}
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
            <BreadcrumbLink>Disposal</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{disposal_id}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      {/* Lock banner */}
      {isLocked && (
        <div className="alert-warning mt-4 flex items-center gap-2">
          <Lock className="size-4 shrink-0" />
          This asset has been disposed and is now locked. No further actions are
          allowed.
        </div>
      )}

      {/* Loading */}
      {isLoading && <DisposalDetailSkeleton />}

      {/* Error */}
      {error && (
        <div className="alert-danger mt-4">{(error as Error).message}</div>
      )}

      {/* Content */}
      {disposal && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
          {/* Left column */}
          <div className="lg:col-span-2 space-y-6">
            {/* Disposal Info */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-wider flex items-center gap-2">
                  <Info className="size-4" />
                  Disposal Info
                </CardTitle>
                <DisposalStatusBadge status={disposal.status} />
              </CardHeader>
              <CardContent>
                <dl className="grid grid-cols-2 gap-4">
                  <div className="col-span-2">
                    <dt className="text-xs font-semibold text-muted-foreground mb-1">
                      Disposal Reason
                    </dt>
                    <dd className="text-sm bg-muted/30 rounded-lg p-3">
                      {disposal.disposal_reason}
                    </dd>
                  </div>
                  <div className="col-span-2">
                    <dt className="text-xs font-semibold text-muted-foreground mb-1">
                      Justification
                    </dt>
                    <dd className="text-sm bg-muted/30 rounded-lg p-3">
                      {disposal.justification}
                    </dd>
                  </div>
                  <DetailItem
                    label="Initiated By"
                    value={disposal.initiated_by}
                  />
                  <DetailItem
                    label="Initiated At"
                    value={formatDate(disposal.initiated_at) || '—'}
                  />
                </dl>
              </CardContent>
            </Card>

            {/* Asset Specs */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-wider">
                  Asset Specs
                </CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="grid grid-cols-2 gap-4">
                  <DetailItem
                    label="Brand"
                    value={disposal.asset_specs?.brand ?? 'N/A'}
                  />
                  <DetailItem
                    label="Model"
                    value={disposal.asset_specs?.model ?? 'N/A'}
                  />
                  <DetailItem
                    label="Serial Number"
                    value={disposal.asset_specs?.serial_number ?? 'N/A'}
                  />
                  <DetailItem
                    label="Product Description"
                    value={disposal.asset_specs?.product_description ?? 'N/A'}
                  />
                  <DetailItem
                    label="Cost"
                    value={
                      disposal.asset_specs?.cost != null
                        ? formatNumber(disposal.asset_specs.cost)
                        : 'N/A'
                    }
                  />
                  <DetailItem
                    label="Purchase Date"
                    value={
                      disposal.asset_specs?.purchase_date
                        ? formatDate(disposal.asset_specs.purchase_date) ||
                        'N/A'
                        : 'N/A'
                    }
                  />
                </dl>
              </CardContent>
            </Card>

            {/* Management Review (conditional) */}
            {disposal.management_reviewed_at && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm uppercase tracking-wider flex items-center gap-2">
                    <ClipboardCheck className="size-4" />
                    Management Review
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <dl className="grid grid-cols-2 gap-4">
                    <DetailItem
                      label="Reviewed By"
                      value={disposal.management_reviewed_by ?? '—'}
                    />
                    <DetailItem
                      label="Reviewed At"
                      value={formatDate(disposal.management_reviewed_at) || '—'}
                    />
                    {disposal.management_approved_at && (
                      <DetailItem
                        label="Approved At"
                        value={
                          formatDate(disposal.management_approved_at) || '—'
                        }
                      />
                    )}
                    {disposal.management_remarks && (
                      <div className="col-span-2">
                        <dt className="text-xs font-semibold text-muted-foreground mb-1">
                          Remarks
                        </dt>
                        <dd className="text-sm bg-muted/30 rounded-lg p-3">
                          {disposal.management_remarks}
                        </dd>
                      </div>
                    )}
                    {disposal.management_rejection_reason && (
                      <div className="col-span-2">
                        <dt className="text-xs font-semibold text-muted-foreground mb-1">
                          Rejection Reason
                        </dt>
                        <dd className="text-sm bg-muted/30 rounded-lg p-3">
                          {disposal.management_rejection_reason}
                        </dd>
                      </div>
                    )}
                  </dl>
                </CardContent>
              </Card>
            )}

            {/* Completion (conditional) */}
            {disposal.completed_at && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm uppercase tracking-wider flex items-center gap-2">
                    <CheckCircle className="size-4" />
                    Completion
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <dl className="grid grid-cols-2 gap-4">
                    <DetailItem
                      label="Disposal Date"
                      value={formatDate(disposal.disposal_date) || '—'}
                    />
                    <div>
                      <dt className="text-xs font-semibold text-muted-foreground mb-1">
                        Data Wipe Confirmed
                      </dt>
                      <dd>
                        <Badge
                          variant={
                            disposal.data_wipe_confirmed ? 'success' : 'danger'
                          }
                        >
                          {disposal.data_wipe_confirmed
                            ? 'Data Wipe Confirmed'
                            : 'Not Confirmed'}
                        </Badge>
                      </dd>
                    </div>
                    <DetailItem
                      label="Completed By"
                      value={disposal.completed_by ?? '—'}
                    />
                    <DetailItem
                      label="Completed At"
                      value={formatDate(disposal.completed_at) || '—'}
                    />
                  </dl>
                </CardContent>
              </Card>
            )}

            {/* Finance Notification (conditional) */}
            {disposal.finance_notification_sent && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm uppercase tracking-wider flex items-center gap-2">
                    <Bell className="size-4" />
                    Finance Notification
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <dl className="grid grid-cols-2 gap-4">
                    <div>
                      <dt className="text-xs font-semibold text-muted-foreground mb-1">
                        Status
                      </dt>
                      <dd>
                        {disposal.finance_notification_status ? (
                          <Badge
                            variant={
                              FinanceNotificationStatusVariants[
                              disposal.finance_notification_status
                              ]
                            }
                          >
                            {
                              FinanceNotificationStatusLabels[
                              disposal.finance_notification_status
                              ]
                            }
                          </Badge>
                        ) : (
                          '—'
                        )}
                      </dd>
                    </div>
                    <DetailItem
                      label="Notified At"
                      value={formatDate(disposal.finance_notified_at) || '—'}
                    />
                  </dl>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right sidebar */}
          <div className="space-y-4">
            {/* Action buttons (hidden when locked) */}
            {!isLocked && (canManagementReview || canCompleteDisposal) && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm uppercase tracking-wider">
                    Actions
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-2">
                  {canManagementReview && (
                    <>
                      <Button
                        className="justify-start"
                        onClick={() => setApproveDialogOpen(true)}
                      >
                        Approve
                      </Button>
                      <Button
                        variant="destructive"
                        className="justify-start"
                        onClick={() => setRejectDialogOpen(true)}
                      >
                        Reject
                      </Button>
                    </>
                  )}
                  {canCompleteDisposal && (
                    <Button
                      className="justify-start"
                      onClick={() => setCompleteDialogOpen(true)}
                    >
                      Complete Disposal
                    </Button>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* Approve/Reject dialogs */}
      <Suspense fallback={null}>
        <ApproveDisposalDialog
          open={approveDialogOpen}
          onOpenChange={setApproveDialogOpen}
          assetId={asset_id}
          disposalId={disposal_id}
        />
        <RejectDisposalDialog
          open={rejectDialogOpen}
          onOpenChange={setRejectDialogOpen}
          assetId={asset_id}
          disposalId={disposal_id}
        />
        {disposal && (
          <CompleteDisposalDialog
            open={completeDialogOpen}
            onOpenChange={setCompleteDialogOpen}
            assetId={asset_id}
            disposalId={disposal_id}
            disposal={{
              disposal_reason: disposal.disposal_reason,
              justification: disposal.justification,
            }}
          />
        )}
      </Suspense>
    </main>
  )
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function DisposalDetailSkeleton() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
      <div className="lg:col-span-2 space-y-6">
        {Array.from({ length: 3 }).map((_, i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-4 w-28" />
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-4">
                {Array.from({ length: 4 }).map((_, j) => (
                  <div key={j} className="space-y-1.5">
                    <Skeleton className="h-3 w-20" />
                    <Skeleton className="h-4 w-32" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <Skeleton className="h-4 w-16" />
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-9 w-full rounded-lg" />
            <Skeleton className="h-9 w-full rounded-lg" />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

// ── Helper ────────────────────────────────────────────────────────────────────

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold text-muted-foreground mb-1">
        {label}
      </dt>
      <dd className="text-sm">{value}</dd>
    </div>
  )
}
