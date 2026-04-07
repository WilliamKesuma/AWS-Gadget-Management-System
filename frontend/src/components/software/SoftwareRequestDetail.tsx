import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import {
  Calendar,
  CheckCircle2,
  Clock,
  FileText,
  Globe,
  Key,
  Monitor,
  Package,
  ShieldAlert,
  User,
  XCircle,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '#/components/ui/card'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Skeleton } from '#/components/ui/skeleton'
import { Separator } from '#/components/ui/separator'
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbSeparator,
  BreadcrumbPage,
} from '#/components/ui/breadcrumb'
import { SoftwareStatusBadge } from './SoftwareStatusBadge'
import { RiskLevelBadge } from './RiskLevelBadge'
import { ITAdminReviewDialog } from './ITAdminReviewDialog'
import { ManagementReviewDialog } from './ManagementReviewDialog'
import { useSoftwareRequestDetail } from '#/hooks/use-software-requests'
import { useCurrentUserRole } from '#/hooks/use-current-user'
import { getSoftwareActionPermissions } from '#/lib/permissions'
import { DataAccessImpactLabels } from '#/lib/models/labels'
import type { DataAccessImpact } from '#/lib/models/types'
import { formatDate } from '#/lib/utils'

type SoftwareRequestDetailProps = {
  assetId: string
  softwareRequestId: string
}

export function SoftwareRequestDetail({
  assetId,
  softwareRequestId,
}: SoftwareRequestDetailProps) {
  const {
    data: request,
    isLoading,
    error,
  } = useSoftwareRequestDetail(assetId, softwareRequestId)
  const role = useCurrentUserRole()
  const [reviewOpen, setReviewOpen] = useState(false)
  const [mgmtReviewOpen, setMgmtReviewOpen] = useState(false)

  if (isLoading) return <SoftwareDetailSkeleton />

  if (error) {
    return <div className="alert-danger">{(error as Error).message}</div>
  }

  if (!request) return null

  const { canITAdminReview, canManagementReview } =
    getSoftwareActionPermissions({
      role,
      status: request.status,
    })

  return (
    <div className="space-y-6">
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
              <Link to="/assets/$asset_id" params={{ asset_id: assetId }}>
                {assetId}
              </Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>Software Request</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      {/* Hero Card */}
      <Card>
        <CardContent className="flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="flex size-14 shrink-0 items-center justify-center rounded-lg bg-info-subtle">
            <Monitor className="size-7 text-info" strokeWidth={1.5} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <h1 className="text-xl font-semibold truncate">
                {request.software_name}
                <span className="text-muted-foreground font-normal ml-1.5">
                  v{request.version}
                </span>
              </h1>
              <SoftwareStatusBadge status={request.status} />
            </div>
            <p className="text-sm text-muted-foreground">
              Asset{' '}
              <Link
                to="/assets/$asset_id"
                params={{ asset_id: assetId }}
                className="text-info font-medium hover:underline"
              >
                {assetId}
              </Link>
              {' · Vendor: '}
              <span className="font-medium text-foreground">
                {request.vendor}
              </span>
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 sm:ml-auto shrink-0">
            {canITAdminReview && (
              <Button size="sm" onClick={() => setReviewOpen(true)}>
                <ShieldAlert className="size-4 mr-1.5" />
                Review Request
              </Button>
            )}
            {canManagementReview && (
              <Button size="sm" onClick={() => setMgmtReviewOpen(true)}>
                Review Escalated Request
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Quick Info Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <QuickInfoCard
          icon={Calendar}
          label="Requested"
          value={formatDate(request.created_at) || '—'}
        />
        <QuickInfoCard
          icon={User}
          label="Requested By"
          value={request.requested_by}
        />
        <QuickInfoCard
          icon={Key}
          label="License Type"
          value={request.license_type}
        />
        <QuickInfoCard
          icon={Clock}
          label="Validity Period"
          value={request.license_validity_period}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Justification */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">
                <FileText className="size-4 inline mr-1.5 -mt-0.5" />
                Justification
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed">{request.justification}</p>
            </CardContent>
          </Card>

          {/* Software Details */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">
                <Package className="size-4 inline mr-1.5 -mt-0.5" />
                Software Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
                <DetailItem
                  label="Software Name"
                  value={request.software_name}
                />
                <DetailItem label="Version" value={request.version} />
                <DetailItem label="Vendor" value={request.vendor} />
                <DetailItem label="License Type" value={request.license_type} />
                <DetailItem
                  label="Validity Period"
                  value={request.license_validity_period}
                />
              </dl>
            </CardContent>
          </Card>

          {/* IT Admin Review */}
          {request.reviewed_by && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">
                  <ShieldAlert className="size-4 inline mr-1.5 -mt-0.5" />
                  IT Admin Review
                </CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
                  <DetailItem label="Reviewed By" value={request.reviewed_by} />
                  <DetailItem
                    label="Reviewed At"
                    value={formatDate(request.reviewed_at) || '—'}
                  />
                  {request.rejection_reason && (
                    <div className="sm:col-span-2">
                      <dt className="text-xs font-semibold text-muted-foreground mb-1">
                        Rejection Reason
                      </dt>
                      <dd className="text-sm text-danger">
                        {request.rejection_reason}
                      </dd>
                    </div>
                  )}
                </dl>
              </CardContent>
            </Card>
          )}

          {/* Management Review */}
          {request.management_reviewed_by && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">
                  Management Review
                </CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
                  <DetailItem
                    label="Reviewed By"
                    value={request.management_reviewed_by}
                  />
                  <DetailItem
                    label="Reviewed At"
                    value={formatDate(request.management_reviewed_at) || '—'}
                  />
                  {request.management_remarks && (
                    <DetailItem
                      label="Remarks"
                      value={request.management_remarks}
                      fullWidth
                    />
                  )}
                  {request.management_rejection_reason && (
                    <div className="sm:col-span-2">
                      <dt className="text-xs font-semibold text-muted-foreground mb-1">
                        Rejection Reason
                      </dt>
                      <dd className="text-sm text-danger">
                        {request.management_rejection_reason}
                      </dd>
                    </div>
                  )}
                </dl>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right sidebar */}
        <div className="space-y-6">
          {/* Risk Assessment */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">
                Risk Assessment
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-xs font-semibold text-muted-foreground mb-1.5">
                  Data Access Impact
                </p>
                <Badge variant="outline">
                  {DataAccessImpactLabels[
                    request.data_access_impact as DataAccessImpact
                  ] ?? request.data_access_impact}
                </Badge>
              </div>
              <Separator />
              <div>
                <p className="text-xs font-semibold text-muted-foreground mb-1.5">
                  IT Risk Level
                </p>
                {request.risk_level ? (
                  <RiskLevelBadge value={request.risk_level} />
                ) : (
                  <span className="text-sm text-muted-foreground">
                    Pending review
                  </span>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Timeline */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">
                Timeline
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="relative border-s border-border ms-2 space-y-6">
                <TimelineItem
                  icon={<Globe className="size-3" />}
                  label="Requested"
                  date={formatDate(request.created_at)}
                  person={request.requested_by}
                  active
                />
                {request.reviewed_by && (
                  <TimelineItem
                    icon={<ShieldAlert className="size-3" />}
                    label="IT Admin Reviewed"
                    date={formatDate(request.reviewed_at)}
                    person={request.reviewed_by}
                    active
                  />
                )}
                {request.management_reviewed_by && (
                  <TimelineItem
                    icon={<User className="size-3" />}
                    label="Management Reviewed"
                    date={formatDate(request.management_reviewed_at)}
                    person={request.management_reviewed_by}
                    active
                  />
                )}
                {request.installation_timestamp && (
                  <TimelineItem
                    icon={<CheckCircle2 className="size-3" />}
                    label="Installed"
                    date={formatDate(request.installation_timestamp)}
                    active
                  />
                )}
                {request.status === 'SOFTWARE_INSTALL_REJECTED' && (
                  <TimelineItem
                    icon={<XCircle className="size-3" />}
                    label="Rejected"
                    date={formatDate(
                      request.management_reviewed_at ?? request.reviewed_at,
                    )}
                    active
                  />
                )}
              </ol>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Dialogs */}
      <ITAdminReviewDialog
        open={reviewOpen}
        onOpenChange={setReviewOpen}
        assetId={assetId}
        softwareRequestId={softwareRequestId}
      />
      <ManagementReviewDialog
        open={mgmtReviewOpen}
        onOpenChange={setMgmtReviewOpen}
        assetId={assetId}
        softwareRequestId={softwareRequestId}
      />
    </div>
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
  icon?: React.ReactNode
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

function SoftwareDetailSkeleton() {
  return (
    <div className="space-y-6">
      {/* Hero */}
      <Card>
        <CardContent className="flex items-center gap-4">
          <Skeleton className="size-14 rounded-lg" />
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-5 w-24 rounded-full" />
            </div>
            <Skeleton className="h-4 w-40" />
          </div>
          <Skeleton className="h-8 w-32" />
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
          <Card>
            <CardHeader>
              <Skeleton className="h-4 w-24" />
            </CardHeader>
            <CardContent className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <Skeleton className="h-4 w-32" />
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="space-y-1.5">
                    <Skeleton className="h-3 w-20" />
                    <Skeleton className="h-4 w-32" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <Skeleton className="h-4 w-28" />
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Skeleton className="h-3 w-24" />
                <Skeleton className="h-5 w-16 rounded-full" />
              </div>
              <Skeleton className="h-px w-full" />
              <div className="space-y-1.5">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-5 w-16 rounded-full" />
              </div>
            </CardContent>
          </Card>
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
