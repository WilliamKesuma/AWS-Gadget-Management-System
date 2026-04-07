import { CalendarIcon, UserCheck, CircleDot, ShieldAlert } from 'lucide-react'
import { Card, CardContent } from '#/components/ui/card'
import type { GetAssetResponse } from '#/lib/models/types'
import { AssetConditionLabels } from '#/lib/models/labels'
import { formatDate } from '#/lib/utils'

function InfoCard({
  icon: Icon,
  label,
  children,
  className,
}: {
  icon: React.ElementType
  label: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <Card className="gap-3 py-4">
      <CardContent className="flex items-start gap-3">
        <Icon
          className="size-4 mt-0.5 text-muted-foreground shrink-0"
          strokeWidth={1.5}
        />
        <div className="space-y-0.5 min-w-0">
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className={`text-sm font-semibold truncate ${className ?? ''}`}>
            {children}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

export function AssetInfoCards({ asset }: { asset: GetAssetResponse }) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
      <InfoCard icon={CalendarIcon} label="Purchase Date">
        {formatDate(asset.purchase_date) || '—'}
      </InfoCard>
      <InfoCard icon={CircleDot} label="Condition">
        {asset.condition
          ? (AssetConditionLabels[asset.condition] ?? asset.condition)
          : '—'}
      </InfoCard>
      {asset.assigned_date ? (
        <InfoCard icon={UserCheck} label="Assigned Date">
          {formatDate(asset.assigned_date) || '—'}
        </InfoCard>
      ) : (
        <InfoCard icon={CalendarIcon} label="Created">
          {formatDate(asset.created_at) || '—'}
        </InfoCard>
      )}
      {asset.rejection_reason && (
        <InfoCard
          icon={ShieldAlert}
          label="Rejection Reason"
          className="text-danger col-span-2 lg:col-span-3"
        >
          {asset.rejection_reason}
        </InfoCard>
      )}
    </div>
  )
}
