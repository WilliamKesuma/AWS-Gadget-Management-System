import { Badge } from '#/components/ui/badge'
import { SoftwareStatusLabels } from '#/lib/models/labels'
import { SoftwareStatusVariants } from '#/lib/models/badge-variants'
import type { SoftwareStatus } from '#/lib/models/types'

export function SoftwareStatusBadge({ status }: { status: SoftwareStatus }) {
  return (
    <Badge variant={SoftwareStatusVariants[status]}>
      {SoftwareStatusLabels[status]}
    </Badge>
  )
}
