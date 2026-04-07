import { Link } from '@tanstack/react-router'
import { HardDrive, Clock, User } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { IssueStatusBadge } from './IssueStatusBadge'
import { formatDate } from '#/lib/utils'
import type { IssueStatus } from '#/lib/models/types'

function deriveTicketId(assetId: string, issueId: string): string {
  const shortId = issueId.slice(-4)
  return `#${assetId}-${shortId}`
}

type IssueCardIssue = {
  asset_id: string
  issue_id: string
  issue_description: string
  status: IssueStatus
  reported_by: string
  created_at: string
}

type IssueCardProps = {
  issue: IssueCardIssue
}

export function IssueCard({ issue }: IssueCardProps) {
  const ticketId = deriveTicketId(issue.asset_id, issue.issue_id)

  return (
    <div className="flex items-start justify-between p-6 border-b last:border-b-0 hover:bg-muted/50 transition-colors">
      <div className="flex flex-col gap-1.5 min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <Link
            to="/assets/$asset_id/issues/$issue_id"
            params={{ asset_id: issue.asset_id, issue_id: issue.issue_id }}
            className="text-xs font-bold text-info hover:underline"
          >
            {issue.issue_id}
          </Link>
          <span className="text-xs font-bold text-muted-foreground">{ticketId}</span>
          <IssueStatusBadge status={issue.status} />
        </div>
        <h3 className="text-lg font-bold truncate">
          {issue.issue_description}
        </h3>
        <div className="flex items-center gap-4 mt-2 text-xs font-semibold text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <HardDrive className="h-3.5 w-3.5" />
            {issue.asset_id}
          </div>
          <div className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" />
            {formatDate(issue.created_at) || '—'}
          </div>
          <div className="flex items-center gap-1.5">
            <User className="h-3.5 w-3.5" />
            {issue.reported_by}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-3 shrink-0 ml-4 mt-4">
        <Button variant="outline" asChild>
          <Link
            to="/assets/$asset_id/issues/$issue_id"
            params={{ asset_id: issue.asset_id, issue_id: issue.issue_id }}
          >
            View Details
          </Link>
        </Button>
      </div>
    </div>
  )
}
