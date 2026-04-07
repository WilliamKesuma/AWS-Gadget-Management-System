import { Box, Ticket, Wrench } from 'lucide-react'
import { Badge } from '#/components/ui/badge'
import { Card, CardHeader, CardTitle } from '#/components/ui/card'
import { StatCard } from '#/components/general/StatCard'
import { formatNumber, formatRelativeTime } from '#/lib/utils'
import { useCurrentUserAttributes } from '#/hooks/use-current-user'
import {
  useITAdminStats,
  useAssetDistribution,
  useRecentActivity,
} from '#/hooks/use-dashboard'
import { Skeleton } from '#/components/ui/skeleton'
import { UserRoleLabels, ActivityTypeLabels } from '#/lib/models/labels'
import {
  ACTIVITY_ICON_MAP,
  ACTIVITY_BADGE_VARIANT,
} from '#/components/dashboard/activity-utils'
import { LastRefreshed } from '#/components/dashboard/LastRefreshed'
import { AssetDistributionChart } from '#/components/dashboard/AssetDistributionChart'

export function ITAdminDashboard() {
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
  } = useITAdminStats()
  const { data: distribution, isLoading: distLoading } = useAssetDistribution()
  const { data: activity, isLoading: activityLoading } = useRecentActivity()

  return (
    <main className="page-base">
      <div>
        <h1 className="page-title">Welcome back, {displayName}</h1>
        <div className="flex items-center gap-3 mt-0.5">
          <p className="page-subtitle">
            Monitor real-time hardware health and support requests.
          </p>
          <LastRefreshed dataUpdatedAt={dataUpdatedAt} />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
        <StatCard
          loading={statsLoading}
          title="Total Assets"
          data={formatNumber(stats?.total_assets ?? 0)}
          Icon={Box}
          iconVariant="info"
        />
        <StatCard
          loading={statsLoading}
          title="Pending Issues"
          data={formatNumber(stats?.pending_issues ?? 0)}
          Icon={Ticket}
          iconVariant="warning"
        />
        <StatCard
          loading={statsLoading}
          title="In Maintenance"
          data={formatNumber(stats?.in_maintenance ?? 0)}
          Icon={Wrench}
          iconVariant="default"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        {/* Recent Activity */}
        <Card className="lg:col-span-2 gap-0 pb-0 flex flex-col">
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
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
                      <p className="text-sm font-semibold truncate">
                        {item.activity}
                      </p>
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
        </Card>

        {/* Asset Distribution */}
        <AssetDistributionChart
          items={distribution?.items}
          isLoading={distLoading}
        />
      </div>
    </main>
  )
}
