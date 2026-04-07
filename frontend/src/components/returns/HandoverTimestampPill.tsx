import { Clock } from 'lucide-react'
import { formatDate } from '#/lib/utils'

type Props = { label: string; timestamp: string }

export function HandoverTimestampPill({ label, timestamp }: Props) {
  return (
    <div className="flex items-center justify-between border border-border rounded-lg px-3 py-2.5">
      <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <div className="flex items-center gap-1.5 text-sm font-medium">
        <Clock className="size-3.5 text-muted-foreground" />
        <span>{formatDate(timestamp) || '—'}</span>
      </div>
    </div>
  )
}
