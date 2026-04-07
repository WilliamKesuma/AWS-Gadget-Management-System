import { useMemo } from 'react'
import { Monitor, ClipboardList, FileCheck, AppWindow, Eye } from 'lucide-react'
import { createColumnHelper, type ColumnDef } from '@tanstack/react-table'
import { Badge } from '#/components/ui/badge'
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '#/components/ui/card'
import { StatCard } from '#/components/general/StatCard'
import { Button } from '#/components/ui/button'
import { DataTable } from '#/components/general/DataTable'
import { Link } from '@tanstack/react-router'
import { useCurrentUserAttributes } from '#/hooks/use-current-user'
import { useEmployeeStats } from '#/hooks/use-dashboard'
import { useAssets } from '#/hooks/use-assets'
import { formatNumber, formatDate } from '#/lib/utils'
import { AssetStatusLabels } from '#/lib/models/labels'
import { AssetStatusVariants } from '#/lib/models/badge-variants'
import { LastRefreshed } from '#/components/dashboard/LastRefreshed'
import type { AssetItem, AssetStatus } from '#/lib/models/types'

const deviceColumnHelper = createColumnHelper<AssetItem>()

export function EmployeeDashboard() {
  const userAttributes = useCurrentUserAttributes()
  const displayName =
    userAttributes?.name ??
    userAttributes?.given_name ??
    userAttributes?.email?.split('@')[0] ??
    'there'

  const { data: stats, isLoading, dataUpdatedAt } = useEmployeeStats()
  const { data: assets, isLoading: assetsLoading } = useAssets({}, undefined, 10)

  const columns = useMemo<ColumnDef<AssetItem, any>[]>(
    () => [
      deviceColumnHelper.display({
        id: 'device',
        header: 'DEVICE',
        cell: ({ row }) => (
          <div className="flex items-center gap-3">
            <Monitor className="size-5 text-muted-foreground shrink-0" />
            <div>
              <p className="font-semibold">
                {row.original.brand} {row.original.model}
              </p>
              {row.original.serial_number && (
                <p className="text-xs text-muted-foreground">
                  SN: {row.original.serial_number}
                </p>
              )}
            </div>
          </div>
        ),
      }),
      deviceColumnHelper.accessor('assignment_date', {
        header: 'ASSIGNED DATE',
        cell: (info) => (
          <span className="text-muted-foreground">
            {formatDate(info.getValue()) || '—'}
          </span>
        ),
      }),
      deviceColumnHelper.accessor('status', {
        header: 'STATUS',
        cell: (info) => {
          const status = info.getValue() as AssetStatus
          return (
            <Badge variant={AssetStatusVariants[status] ?? 'info'} size="sm">
              {AssetStatusLabels[status]}
            </Badge>
          )
        },
      }),
      deviceColumnHelper.display({
        id: 'actions',
        header: '',
        cell: ({ row }) => (
          <Button asChild variant="ghost" size="icon">
            <Link
              to="/assets/$asset_id"
              params={{ asset_id: row.original.asset_id }}
            >
              <Eye className="size-4" />
            </Link>
          </Button>
        ),
      }),
    ],
    [],
  )

  const deviceData = useMemo(() => assets?.items ?? [], [assets])

  return (
    <main className="page-base">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Welcome back, {displayName}</h1>
          <LastRefreshed dataUpdatedAt={dataUpdatedAt} />
        </div>
        <div className="flex items-center gap-3">
          <Button variant="default" size="sm" asChild>
            <Link to="/requests/new-issue">Report Issue</Link>
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
        <StatCard
          loading={isLoading}
          title="My Pending Requests"
          data={formatNumber(stats?.my_pending_requests ?? 0)}
          Icon={ClipboardList}
          iconVariant="info"
        />
        <StatCard
          loading={isLoading}
          title="Assigned Assets"
          data={formatNumber(stats?.assigned_assets ?? 0)}
          Icon={Monitor}
          iconVariant="info"
        />
        <StatCard
          loading={isLoading}
          title="Documents to Sign"
          data={formatNumber(stats?.pending_signatures ?? 0)}
          Icon={FileCheck}
          iconVariant="default"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        {/* Current Assigned Devices */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-lg font-bold">Current Assigned Devices</h2>
            <Badge variant="secondary" size="sm">
              {deviceData.length} Assets
            </Badge>
          </div>
          <DataTable
            columns={columns}
            data={deviceData}
            pageSize={deviceData.length || 10}
            entityName="devices"
            isLoading={assetsLoading}
          />
        </div>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Button
              variant="outline"
              size="sm"
              className="justify-start"
              asChild
            >
              <Link to="/requests/new-software">
                <AppWindow className="size-4" />
                Software Request
              </Link>
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="justify-start"
              asChild
            >
              <Link to="/requests/new-issue">
                <ClipboardList className="size-4" />
                Report Issue
              </Link>
            </Button>
          </CardContent>
          <CardFooter className="justify-center">
            <Button variant="link" size="sm" asChild>
              <Link to="/assets">View all assets</Link>
            </Button>
          </CardFooter>
        </Card>
      </div>
    </main>
  )
}
