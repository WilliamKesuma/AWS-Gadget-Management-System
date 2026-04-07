import React from 'react'
import { type LucideIcon } from 'lucide-react'
import { Card, CardContent } from '../ui/card'
import { Skeleton } from '../ui/skeleton'

export interface StatCardProps {
  title: string
  data: string | number
  Icon: LucideIcon
  iconVariant?: 'info' | 'warning' | 'danger' | 'default'
  badge?: React.ReactNode
  loading?: boolean
}

const ICON_VARIANT_CLASSES: Record<NonNullable<StatCardProps['iconVariant']>, { bg: string; color: string }> = {
  info: { bg: 'bg-info-subtle', color: 'text-info' },
  warning: { bg: 'bg-warning-subtle', color: 'text-warning' },
  danger: { bg: 'bg-danger-subtle', color: 'text-danger' },
  default: { bg: 'bg-muted', color: 'text-muted-foreground' },
}

export function StatCard({
  title,
  data,
  Icon,
  iconVariant = 'info',
  badge,
  loading = false,
}: StatCardProps) {
  const { bg, color } = ICON_VARIANT_CLASSES[iconVariant]
  return (
    <Card className="flex flex-col gap-4 relative">
      <CardContent>
        {badge && <div className="absolute top-6 right-6">{badge}</div>}
        <div className="flex items-center gap-4">
          {loading ? (
            <>
              <Skeleton className="h-10 w-10 rounded-lg shrink-0" />
              <div className="flex flex-col gap-1.5">
                <Skeleton className="h-3.5 w-24" />
                <Skeleton className="h-6 w-16" />
              </div>
            </>
          ) : (
            <>
              <div
                className={`h-10 w-10 rounded-lg ${bg} flex items-center justify-center ${color}`}
              >
                <Icon className="h-5 w-5" />
              </div>
              <div>
                <h2 className="card-title">{title}</h2>
                <h3 className="card-data">{data}</h3>
              </div>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
