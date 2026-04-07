import { Badge } from '#/components/ui/badge'
import { ReturnConditionLabels } from '#/lib/models/labels'
import { ReturnConditionVariants } from '#/lib/models/badge-variants'
import type { ReturnCondition } from '#/lib/models/types'

type Props = { condition: ReturnCondition | undefined }

export function ReturnConditionBadge({ condition }: Props) {
  if (!condition) return <Badge variant="warning">Unknown</Badge>
  return (
    <Badge variant={ReturnConditionVariants[condition]}>
      {ReturnConditionLabels[condition]}
    </Badge>
  )
}
