import { useMemo } from 'react'
import { Box, ClipboardCheck, Archive } from 'lucide-react'
import { createColumnHelper, type ColumnDef } from '@tanstack/react-table'
import { Badge } from '#/components/ui/badge'
import { Card } from '#/components/ui/card'
import { StatCard } from '#/components/general/StatCard'
import { Button } from '#/components/ui/button'
import { DataTable } from '#/components/general/DataTable'
import { Link } from '@tanstack/react-router'
import { formatNumber, formatRelativeTime } from '#/lib/utils'
import { useCurrentUserAttributes } from '#/hooks/use-current-user'
import {
  useManagementStats,
  useAssetDistribution,
  useRecentActivity,
  useApprovalHub,
} from '#/hooks/use-dashboard'
import { Skeleton } from '#/components/ui/skeleton'
import {
  UserRoleLabels,
  ActivityTypeLabels,
  ApprovalTypeLabels,
} from '#/lib/models/labels'
import {
  ACTIVITY_ICON_MAP,
  ACTIVITY_BADGE_VARIANT,
} from '#/components/dashboard/activity-utils'
import { LastRefreshed } from '#/components/dashboard/LastRefreshed'
import { AssetDistributionChart } from '#/components/dashboard/AssetDistributionChart'
import type { ApprovalHubItem, ApprovalType } from '#/lib/models/types'

const APPROVAL_BADGE_VARIANT: Record<string, 'info' | 'warning' | 'danger'> = {
  ASSET_CREATION: 'info',
  REPLACEMENT: 'warning',
  SOFTWARE_ESCALATION: 'info',
  DISPOSAL: 'danger',
}

const approvalColumnHelper = createColumnHelper<ApprovalHubItem>()

export function ManagementDashboard() {
  const userAttributes = useCurrentUserAttributes()
  const displayName =
    userAttributes?.name ??
    userAttributes?.given_name ??
    userAttributes?.email?.split('@')[0] ??
    'there'

  const {
    data: stats,
    isLoading: statsLoading,
    dataUpdatedAt,
  } = useManagementStats()
  const { data: distribution, isLoading: distLoading } = useAssetDistribution()
  const { data: activity, isLoading: activityLoading } = useRecentActivity()
  const { data: approvals, isLoading: approvalsLoading } = useApprovalHub()

  const columns = useMemo<ColumnDef<ApprovalHubItem, any>[]>(
    () => [
      approvalColumnHelper.accessor('approval_type', {
        header: 'TYPE',
        cell: (info) => {
          const type = info.getValue() as ApprovalType
          return (
            <Badge
              variant={APPROVAL_BADGE_VARIANT[type] ?? 'secondary'}
              size="sm"
            >
              {ApprovalTypeLabels[type] ?? type}
            </Badge>
          )
        },
      }),
      approvalColumnHelper.display({
        id: 'item',
        header: 'ITEM / REQUEST',
        cell: ({ row }) => (
          <div>
            <p className="font-semibold">{row.original.title}</p>
            <p className="text-xs text-muted-foreground">
              {row.original.subtitle}
            </p>
          </div>
        ),
      }),
      approvalColumnHelper.accessor('requester_name', {
        header: 'REQUESTER',
        cell: (info) => (
          <span className="text-muted-foreground">{info.getValue()}</span>
        ),
      }),
      approvalColumnHelper.display({
        id: 'status',
        header: 'STATUS',
        cell: () => (
          <Badge variant="warning" size="sm">
            Pending
          </Badge>
        ),
      }),
      approvalColumnHelper.display({
        id: 'actions',
        header: 'ACTION',
        cell: () => (
          <Button variant="link" size="sm" className="p-0 h-auto" asChild>
            <Link to="/approvals">Review</Link>
          </Button>
        ),
      }),
    ],
    [],
  )

  const approvalData = useMemo(() => approvals?.items ?? [], [approvals])

  return (
    <main className="page-base">
      <div>
        <h1 className="page-title">Welcome back, {displayName}</h1>
        <div className="flex items-center gap-3 mt-0.5">
          <p className="page-subtitle">
            High-level oversight of gadget lifecycle and departmental
            distributions.
          </p>
          <LastRefreshed dataUpdatedAt={dataUpdatedAt} />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
        <StatCard
          loading={statsLoading}
          title="Total Assets"
          data={formatNumber(stats?.total_assets ?? 0)}
          Icon={Box}
          iconVariant="info"
        />
        <StatCard
          loading={statsLoading}
          title="Pending Approvals"
          data={formatNumber(stats?.pending_approvals ?? 0)}
          Icon={ClipboardCheck}
          iconVariant="warning"
        />
        <StatCard
          loading={statsLoading}
          title="Scheduled Disposals"
          data={formatNumber(stats?.scheduled_disposals ?? 0)}
          Icon={Archive}
          iconVariant="danger"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        {/* Approval Hub */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-lg font-bold">Approval Hub</h2>
            <Button variant="link" size="sm" asChild>
              <Link to="/approvals">View all</Link>
            </Button>
          </div>
          <DataTable
            columns={columns}
            data={approvalData}
            pageSize={approvalData.length}
            entityName="approvals"
            isLoading={approvalsLoading}
          />
        </div>

        {/* Asset Distribution */}
        <AssetDistributionChart
          items={distribution?.items}
          isLoading={distLoading}
        />
      </div>

      {/* Recent Activity */}
      <div className="flex flex-col gap-2 mt-4">
        <h2 className="text-lg font-bold">Recent Activity</h2>
        <Card className="pt-0">
          <div className="flex flex-col">
            {activityLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className="flex items-center gap-4 px-6 py-4 border-b last:border-b-0"
                >
                  <Skeleton className="h-10 w-10 rounded-full shrink-0" />
                  <div className="flex-1 space-y-1.5">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-3 w-1/2" />
                  </div>
                </div>
              ))
            ) : activity?.items.length ? (
              activity.items.map((item) => {
                const iconConfig = ACTIVITY_ICON_MAP[item.activity_type]
                const Icon = iconConfig.icon
                return (
                  <div
                    key={item.activity_id}
                    className="flex items-center gap-4 px-6 py-4 border-b last:border-b-0 hover:bg-muted/50 transition-colors"
                  >
                    <div
                      className={`h-10 w-10 rounded-full ${iconConfig.bg} flex items-center justify-center ${iconConfig.color} shrink-0`}
                    >
                      <Icon className="h-5 w-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-bold">{item.activity}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {item.actor_name} ({UserRoleLabels[item.actor_role]}) ·{' '}
                        {formatRelativeTime(item.timestamp)}
                      </p>
                    </div>
                    <Badge
                      variant={
                        ACTIVITY_BADGE_VARIANT[item.activity_type] ??
                        'secondary'
                      }
                      size="sm"
                    >
                      {ActivityTypeLabels[item.activity_type]}
                    </Badge>
                  </div>
                )
              })
            ) : (
              <p className="px-6 py-8 text-sm text-muted-foreground text-center">
                No recent activity
              </p>
            )}
          </div>
          {/* <CardFooter className="justify-center">
            <Button variant="link" size="sm" asChild>
              <Link to="/audits">View full audit history</Link>
            </Button>
          </CardFooter> */}
        </Card>
      </div>
    </main>
  )
}
