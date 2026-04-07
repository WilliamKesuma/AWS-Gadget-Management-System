import { Info, CalendarClock, MessageSquare } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '#/components/ui/card'
import type { GetAssetResponse } from '#/lib/models/types'
import { formatDate } from '#/lib/utils'

export function AdditionalInfoCard({ asset }: { asset: GetAssetResponse }) {
  const hasContent = asset.remarks || asset.created_at

  if (!hasContent) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <Info className="size-4 text-muted-foreground" strokeWidth={1.5} />
          Additional Information
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-x-6 gap-y-3">
          {asset.created_at && (
            <div className="space-y-0.5">
              <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                <CalendarClock className="size-3" />
                Created
              </p>
              <p className="text-sm font-medium">
                {formatDate(asset.created_at) || '—'}
              </p>
            </div>
          )}
          {asset.remarks && (
            <div className="space-y-0.5 col-span-2">
              <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                <MessageSquare className="size-3" />
                Remarks
              </p>
              <p className="text-sm font-medium">{asset.remarks}</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
