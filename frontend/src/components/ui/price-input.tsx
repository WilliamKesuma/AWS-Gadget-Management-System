import * as React from 'react'
import { cn, formatNumber } from '#/lib/utils'

// ─── Component ────────────────────────────────────────────────────────────────

export interface PriceInputProps extends Omit<
  React.ComponentProps<'input'>,
  'value' | 'onChange' | 'type'
> {
  value: number
  onValueChange: (value: number) => void
}

function PriceInput({
  value,
  onValueChange,
  className,
  onBlur,
  ...props
}: PriceInputProps) {
  const [display, setDisplay] = React.useState(() =>
    value ? formatNumber(value) : '',
  )
  const [focused, setFocused] = React.useState(false)

  // Sync display when value changes externally (and not focused)
  React.useEffect(() => {
    if (!focused) {
      setDisplay(value ? formatNumber(value) : '')
    }
  }, [value, focused])

  function handleFocus() {
    setFocused(true)
    setDisplay(value === 0 ? '' : String(value))
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const raw = e.target.value.replace(/[^\d]/g, '')
    if (raw === '') {
      setDisplay('')
      onValueChange(0)
      return
    }
    const num = Number(raw)
    if (Number.isNaN(num)) return
    setDisplay(formatNumber(num))
    onValueChange(num)
  }

  function handleBlur(e: React.FocusEvent<HTMLInputElement>) {
    setFocused(false)
    setDisplay(value ? formatNumber(value) : '')
    onBlur?.(e)
  }

  return (
    <input
      type="text"
      inputMode="numeric"
      data-slot="input"
      value={display}
      onFocus={handleFocus}
      onChange={handleChange}
      onBlur={handleBlur}
      placeholder="0"
      className={cn(
        'h-9 w-full min-w-0 rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none selection:bg-primary selection:text-primary-foreground placeholder:text-muted-foreground disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm dark:bg-input/30',
        'focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50',
        'aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40',
        className,
      )}
      {...props}
    />
  )
}

export { PriceInput }
