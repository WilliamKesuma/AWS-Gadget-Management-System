import { Database } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '#/components/ui/select'
import { ReturnConditionLabels } from '#/lib/models/labels'
import type { ReturnCondition } from '#/lib/models/types'

type Props = {
  model: string | undefined
  serialNumber: string | undefined
  mode: 'edit' | 'readonly'
  conditionValue?: ReturnCondition | ''
  onConditionChange?: (value: ReturnCondition) => void
  conditionInvalid?: boolean
}

export function AssetDetailsCard({
  model,
  serialNumber,
  mode,
  conditionValue,
  onConditionChange,
  conditionInvalid,
}: Props) {
  return (
    <div className="bg-info/10 border border-info/20 rounded-lg p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Database className="size-4 text-info" />
        <span className="text-xs font-bold uppercase tracking-wider text-info">
          Asset Details
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">
            Model
          </p>
          <p className="text-sm font-medium">{model || 'N/A'}</p>
        </div>
        <div>
          <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">
            Serial No.
          </p>
          <p className="text-sm font-medium">{serialNumber || 'N/A'}</p>
        </div>
      </div>

      {mode === 'edit' && (
        <div>
          <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-1">
            Condition Assessment
          </p>
          <Select
            value={conditionValue ?? ''}
            onValueChange={(v) => onConditionChange?.(v as ReturnCondition)}
          >
            <SelectTrigger aria-invalid={conditionInvalid} className="w-full">
              <SelectValue placeholder="Select condition..." />
            </SelectTrigger>
            <SelectContent>
              {(Object.keys(ReturnConditionLabels) as ReturnCondition[]).map(
                (c) => (
                  <SelectItem key={c} value={c}>
                    {ReturnConditionLabels[c]}
                  </SelectItem>
                ),
              )}
            </SelectContent>
          </Select>
        </div>
      )}

      {mode === 'readonly' && conditionValue && (
        <div>
          <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-0.5">
            Condition Assessment
          </p>
          <p className="text-sm font-medium">
            {ReturnConditionLabels[conditionValue as ReturnCondition]}
          </p>
        </div>
      )}
    </div>
  )
}
