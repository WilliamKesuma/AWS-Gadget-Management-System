import { useMemo } from 'react'
import {
  Pie,
  PieChart,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '#/components/ui/card'
import { Skeleton } from '#/components/ui/skeleton'
import { formatNumber } from '#/lib/utils'
import type { AssetDistributionItem } from '#/lib/models/types'

const COLORS = [
  'hsl(221, 83%, 53%)', // blue
  'hsl(160, 84%, 39%)', // emerald
  'hsl(35, 92%, 60%)', // orange
  'hsl(263, 70%, 50%)', // violet
  'hsl(215, 14%, 50%)', // slate
]

interface AssetDistributionChartProps {
  items: AssetDistributionItem[] | undefined
  isLoading: boolean
}

export function AssetDistributionChart({
  items,
  isLoading,
}: AssetDistributionChartProps) {
  const chartData = useMemo(
    () =>
      (items ?? []).map((item, i) => ({
        ...item,
        fill: COLORS[i % COLORS.length],
      })),
    [items],
  )

  const total = useMemo(
    () => chartData.reduce((sum, d) => sum + d.count, 0),
    [chartData],
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle>Asset Distribution</CardTitle>
        <CardDescription>Top 5 count of Asset categories</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center h-[260px]">
            <Skeleton className="h-[200px] w-[200px] rounded-full" />
          </div>
        ) : chartData.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-12">
            No data available
          </p>
        ) : (
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  dataKey="count"
                  nameKey="category"
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  strokeWidth={0}
                >
                  {chartData.map((entry, i) => (
                    <Cell
                      key={entry.category}
                      fill={COLORS[i % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null
                    const data = payload[0]
                    const pct =
                      total > 0
                        ? ((Number(data.value) / total) * 100).toFixed(1)
                        : '0'
                    return (
                      <div className="rounded-lg border bg-background px-3 py-2 shadow-sm">
                        <p className="text-sm font-semibold">{data.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatNumber(Number(data.value))} assets ({pct}%)
                        </p>
                      </div>
                    )
                  }}
                />
                <Legend
                  verticalAlign="bottom"
                  formatter={(value: string) => {
                    const item = chartData.find((d) => d.category === value)
                    return (
                      <span className="text-xs text-muted-foreground">
                        {value} ({formatNumber(item?.count ?? 0)})
                      </span>
                    )
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
