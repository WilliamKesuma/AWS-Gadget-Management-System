import { Badge } from '#/components/ui/badge'
import { ReturnStatusLabels } from '#/lib/models/labels'
import { ReturnStatusVariants } from '#/lib/models/badge-variants'
import type { ReturnStatus } from '#/lib/models/types'

type Props = { status: ReturnStatus | undefined }

export function ReturnStatusBadge({ status }: Props) {
  if (!status) return <Badge variant="warning">Pending</Badge>
  return (
    <Badge variant={ReturnStatusVariants[status]}>
      {ReturnStatusLabels[status]}
    </Badge>
  )
}
