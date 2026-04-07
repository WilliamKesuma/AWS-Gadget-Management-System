import { Badge } from '#/components/ui/badge'
import { AssetStatusLabels } from '#/lib/models/labels'
import { AssetStatusVariants } from '#/lib/models/badge-variants'
import type { AssetStatus } from '#/lib/models/types'

export function DisposalStatusBadge({ status }: { status: AssetStatus }) {
  return (
    <Badge variant={AssetStatusVariants[status] ?? 'default'}>
      {AssetStatusLabels[status]}
    </Badge>
  )
}
