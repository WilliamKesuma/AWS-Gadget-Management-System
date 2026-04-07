import { Badge } from '#/components/ui/badge'
import { RiskLevelLabels } from '#/lib/models/labels'
import { RiskLevelVariants } from '#/lib/models/badge-variants'
import type { RiskLevel } from '#/lib/models/types'

export function RiskLevelBadge({
  value,
}: {
  value: RiskLevel | null | undefined
}) {
  if (!value) return <span>—</span>
  return (
    <Badge variant={RiskLevelVariants[value]}>{RiskLevelLabels[value]}</Badge>
  )
}
