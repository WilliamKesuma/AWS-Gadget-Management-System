import { Card, CardHeader, CardTitle, CardContent } from '#/components/ui/card'
import { Avatar, AvatarFallback } from '#/components/ui/avatar'
import type { AssigneeInfo } from '#/lib/models/types'
import { UserRoleLabels } from '#/lib/models/labels'

function getInitials(name: string) {
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

export function CurrentAssigneeCard({ assignee }: { assignee: AssigneeInfo }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Current Assignee</CardTitle>
      </CardHeader>
      <CardContent className="flex items-center gap-3">
        <Avatar size="lg">
          <AvatarFallback>{getInitials(assignee.fullname)}</AvatarFallback>
        </Avatar>
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">{assignee.fullname}</p>
          <p className="text-xs text-muted-foreground">
            {UserRoleLabels[assignee.role]}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
