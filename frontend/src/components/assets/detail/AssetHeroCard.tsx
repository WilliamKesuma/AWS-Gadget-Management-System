import { Laptop, Smartphone, Tablet, Package } from 'lucide-react'
import { Card, CardContent } from '#/components/ui/card'
import { Badge } from '#/components/ui/badge'
import type { GetAssetResponse, AssetStatus } from '#/lib/models/types'
import { AssetStatusLabels } from '#/lib/models/labels'
import { AssetStatusVariants } from '#/lib/models/badge-variants'

function getCategoryIcon(category?: string) {
  switch (category) {
    case 'LAPTOP':
      return Laptop
    case 'MOBILE_PHONE':
      return Smartphone
    case 'TABLET':
      return Tablet
    default:
      return Package
  }
}

function getStatusVariant(status: AssetStatus) {
  return AssetStatusVariants[status] ?? 'info'
}

export function AssetHeroCard({ asset }: { asset: GetAssetResponse }) {
  const displayName = [asset.brand, asset.model].filter(Boolean).join(' ')
  const CategoryIcon = getCategoryIcon(asset.category)

  return (
    <Card>
      <CardContent className="flex items-center gap-4">
        <div className="flex size-16 shrink-0 items-center justify-center rounded-xl bg-muted">
          <CategoryIcon
            className="size-8 text-muted-foreground"
            strokeWidth={1.5}
          />
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-semibold truncate">
            {displayName || 'Unnamed Asset'}
          </h1>
          <div className="flex items-center gap-3 mt-1 flex-wrap">
            <p className="text-sm text-muted-foreground">
              <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded text-foreground">
                {asset.asset_id}
              </span>
            </p>
          </div>
        </div>
        <Badge variant={getStatusVariant(asset.status)} size="lg">
          {AssetStatusLabels[asset.status]}
        </Badge>
      </CardContent>
    </Card>
  )
}
