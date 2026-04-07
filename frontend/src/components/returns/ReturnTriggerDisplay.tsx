import {
  UserMinus,
  RefreshCw,
  ArrowRightLeft,
  MonitorX,
  ArrowUpCircle,
} from 'lucide-react'
import { ReturnTriggerLabels } from '#/lib/models/labels'
import type { ReturnTrigger } from '#/lib/models/types'

const TRIGGER_ICONS: Record<ReturnTrigger, React.ReactNode> = {
  RESIGNATION: <UserMinus className="size-4 text-muted-foreground" />,
  REPLACEMENT: <RefreshCw className="size-4 text-muted-foreground" />,
  TRANSFER: <ArrowRightLeft className="size-4 text-muted-foreground" />,
  IT_RECALL: <MonitorX className="size-4 text-muted-foreground" />,
  UPGRADE: <ArrowUpCircle className="size-4 text-muted-foreground" />,
}

type Props = { trigger: ReturnTrigger }

export function ReturnTriggerDisplay({ trigger }: Props) {
  return (
    <div className="flex items-center gap-2.5 border border-border rounded-lg px-3 py-2.5">
      {TRIGGER_ICONS[trigger]}
      <span className="text-sm font-medium">
        {ReturnTriggerLabels[trigger]}
      </span>
    </div>
  )
}
