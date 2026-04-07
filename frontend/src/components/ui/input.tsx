import * as React from 'react'

import { cn, formatNumber, parseFormattedNumber } from '#/lib/utils'

const inputClassName =
  'h-9 w-full min-w-0 rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none selection:bg-primary selection:text-primary-foreground file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm dark:bg-input/30'

const inputFocusClassName =
  'focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50'

const inputInvalidClassName =
  'aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40'

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        inputClassName,
        inputFocusClassName,
        inputInvalidClassName,
        className,
      )}
      {...props}
    />
  )
}

// ---------------------------------------------------------------------------
// NumberInput — live-formatted numeric input (20.000 / 20.000.000)
// ---------------------------------------------------------------------------

type NumberInputProps = Omit<
  React.ComponentProps<'input'>,
  'type' | 'value' | 'onChange'
> & {
  /** Raw numeric value (unformatted). */
  value: number | undefined
  /** Called with the raw numeric value on every change. */
  onChange: (value: number | undefined) => void
}

function NumberInput({
  className,
  value,
  onChange,
  ...props
}: NumberInputProps) {
  const inputRef = React.useRef<HTMLInputElement>(null)
  const [display, setDisplay] = React.useState(() =>
    value != null ? formatNumber(value) : '',
  )

  // Sync display when the external value changes (e.g. form reset)
  const prevValue = React.useRef(value)
  React.useEffect(() => {
    if (prevValue.current !== value) {
      prevValue.current = value
      setDisplay(value != null ? formatNumber(value) : '')
    }
  }, [value])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const el = e.target
    const caretBefore = el.selectionStart ?? 0
    const digitsBeforeCaret = el.value
      .slice(0, caretBefore)
      .replace(/[^\d]/g, '').length

    const raw = el.value.replace(/[^\d]/g, '')
    if (raw === '') {
      prevValue.current = undefined
      setDisplay('')
      onChange(undefined)
      return
    }
    const num = Number(raw)
    if (Number.isNaN(num)) return

    const nextDisplay = formatNumber(num)
    prevValue.current = num
    setDisplay(nextDisplay)
    onChange(num)

    // Compute new caret: walk formatted string until we pass the same number of digits
    let seen = 0
    let newCaret = nextDisplay.length
    for (let i = 0; i < nextDisplay.length; i++) {
      if (/\d/.test(nextDisplay[i])) seen++
      if (seen === digitsBeforeCaret) {
        newCaret = i + 1
        break
      }
    }

    requestAnimationFrame(() => {
      inputRef.current?.setSelectionRange(newCaret, newCaret)
    })
  }

  return (
    <input
      ref={inputRef}
      inputMode="numeric"
      data-slot="input"
      className={cn(
        inputClassName,
        inputFocusClassName,
        inputInvalidClassName,
        className,
      )}
      value={display}
      onChange={handleChange}
      {...props}
    />
  )
}

export { Input, NumberInput, parseFormattedNumber }
