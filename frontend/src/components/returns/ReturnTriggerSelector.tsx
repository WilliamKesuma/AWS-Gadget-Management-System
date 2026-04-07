import {
  UserMinus,
  RefreshCw,
  ArrowRightLeft,
  MonitorX,
  ArrowUpCircle,
} from 'lucide-react'
import { ReturnTriggerLabels } from '#/lib/models/labels'
import type { ReturnTrigger } from '#/lib/models/types'
import { cn } from '#/lib/utils'

type TriggerOption = {
  value: ReturnTrigger
  icon: React.ReactNode
  fullWidth?: boolean
}

const TRIGGER_OPTIONS: TriggerOption[] = [
  { value: 'RESIGNATION', icon: <UserMinus className="size-5" /> },
  { value: 'REPLACEMENT', icon: <RefreshCw className="size-5" /> },
  { value: 'TRANSFER', icon: <ArrowRightLeft className="size-5" /> },
  { value: 'IT_RECALL', icon: <MonitorX className="size-5" /> },
  {
    value: 'UPGRADE',
    icon: <ArrowUpCircle className="size-5" />,
    fullWidth: true,
  },
]

type Props = {
  value: ReturnTrigger | ''
  onChange: (value: ReturnTrigger) => void
  disabled?: boolean
}

export function ReturnTriggerSelector({ value, onChange, disabled }: Props) {
  const gridItems = TRIGGER_OPTIONS.filter((o) => !o.fullWidth)
  const fullWidthItem = TRIGGER_OPTIONS.find((o) => o.fullWidth)

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-2">
        {gridItems.map((opt) => (
          <TriggerButton
            key={opt.value}
            option={opt}
            selected={value === opt.value}
            disabled={disabled}
            onClick={() => onChange(opt.value)}
          />
        ))}
      </div>
      {fullWidthItem && (
        <TriggerButton
          option={fullWidthItem}
          selected={value === fullWidthItem.value}
          disabled={disabled}
          onClick={() => onChange(fullWidthItem.value)}
          className="w-full"
        />
      )}
    </div>
  )
}

function TriggerButton({
  option,
  selected,
  disabled,
  onClick,
  className,
}: {
  option: TriggerOption
  selected: boolean
  disabled?: boolean
  onClick: () => void
  className?: string
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        'border rounded-lg p-3 flex flex-col items-center gap-1.5 text-sm cursor-pointer transition-colors',
        selected
          ? 'border-primary bg-primary/10 text-primary'
          : 'border-border text-muted-foreground hover:border-primary/50',
        disabled && 'opacity-50 cursor-not-allowed',
        className,
      )}
    >
      {option.icon}
      <span className="font-medium text-xs">
        {ReturnTriggerLabels[option.value]}
      </span>
    </button>
  )
}
