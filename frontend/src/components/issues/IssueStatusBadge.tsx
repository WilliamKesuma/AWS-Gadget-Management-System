import { Badge } from '#/components/ui/badge'
import { IssueStatusLabels } from '#/lib/models/labels'
import { IssueStatusVariants } from '#/lib/models/badge-variants'
import type { IssueStatus } from '#/lib/models/types'

export function IssueStatusBadge({ status }: { status: IssueStatus }) {
  return (
    <Badge variant={IssueStatusVariants[status]}>
      {IssueStatusLabels[status]}
    </Badge>
  )
}
