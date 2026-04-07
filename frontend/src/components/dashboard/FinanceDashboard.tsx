import { Archive, Wallet, Clock } from 'lucide-react'
import { StatCard } from '#/components/general/StatCard'
import { useCurrentUserAttributes } from '#/hooks/use-current-user'
import { useFinanceStats } from '#/hooks/use-dashboard'
import { formatNumber } from '#/lib/utils'
import { LastRefreshed } from '#/components/dashboard/LastRefreshed'

export function FinanceDashboard() {
  const userAttributes = useCurrentUserAttributes()
  const displayName =
    userAttributes?.name ??
    userAttributes?.given_name ??
    userAttributes?.email?.split('@')[0] ??
    'there'

  const { data: stats, isLoading, dataUpdatedAt } = useFinanceStats()

  return (
    <main className="page-base">
      <div>
        <h1 className="page-title">Welcome back, {displayName}</h1>
        <div className="flex items-center gap-3 mt-0.5">
          <p className="page-subtitle">
            Track asset lifecycle, recovery values, and disposal approvals.
          </p>
          <LastRefreshed dataUpdatedAt={dataUpdatedAt} />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
        <StatCard
          loading={isLoading}
          title="Total Disposed"
          data={formatNumber(stats?.total_disposed ?? 0)}
          Icon={Archive}
          iconVariant="info"
        />
        <StatCard
          loading={isLoading}
          title="Total Asset Value"
          data={formatNumber(stats?.total_asset_value ?? 0)}
          Icon={Wallet}
          iconVariant="default"
        />
        <StatCard
          loading={isLoading}
          title="Pending Write-offs"
          data={formatNumber(stats?.pending_writeoffs ?? 0)}
          Icon={Clock}
          iconVariant="warning"
        />
      </div>
    </main>
  )
}
