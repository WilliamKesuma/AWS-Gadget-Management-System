import { Badge } from '#/components/ui/badge'
import { ResetStatusLabels } from '#/lib/models/labels'
import { ResetStatusVariants } from '#/lib/models/badge-variants'
import type { ResetStatus } from '#/lib/models/types'

type Props = { status: ResetStatus | undefined }

export function ResetStatusBadge({ status }: Props) {
  if (!status) return <Badge variant="warning">Unknown</Badge>
  return (
    <Badge variant={ResetStatusVariants[status]}>
      {ResetStatusLabels[status]}
    </Badge>
  )
}
