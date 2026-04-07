import { clsx } from 'clsx'
import type { ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// ---------------------------------------------------------------------------
// Date formatter — "23 Mar 2025"
// ---------------------------------------------------------------------------

const DATE_FORMATTER = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

/**
 * Formats a Date, ISO string, or timestamp into "23 Mar 2025".
 * Returns an empty string for nullish / invalid input.
 */
export function formatDate(
  value: Date | string | number | null | undefined,
): string {
  if (value == null) return ''
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return DATE_FORMATTER.format(date)
}

// ---------------------------------------------------------------------------
// Number formatter — dot as thousands separator, no decimals (20.000)
// ---------------------------------------------------------------------------

const NUMBER_FORMATTER = new Intl.NumberFormat('de-DE', {
  maximumFractionDigits: 0,
  useGrouping: true,
})

/**
 * Formats a number into "20.000" / "20.000.000" (dot-grouped, no decimals).
 * Returns an empty string for nullish / NaN input.
 */
export function formatNumber(
  value: number | string | null | undefined,
): string {
  if (value == null) return ''
  const num =
    typeof value === 'string' ? Number(value.replace(/\./g, '')) : value
  if (Number.isNaN(num)) return ''
  return NUMBER_FORMATTER.format(Math.round(num))
}

/**
 * Strips formatting dots and returns the raw numeric value, or `undefined`
 * if the string is empty / not a valid number.
 */
export function parseFormattedNumber(formatted: string): number | undefined {
  const raw = formatted.replace(/\./g, '').trim()
  if (raw === '') return undefined
  const num = Number(raw)
  return Number.isNaN(num) ? undefined : num
}

// ---------------------------------------------------------------------------
// Relative time — "2 mins ago", "3 hours ago", "5 days ago"
// ---------------------------------------------------------------------------

const RELATIVE_UNITS: [string, number][] = [
  ['year', 31_536_000],
  ['month', 2_592_000],
  ['week', 604_800],
  ['day', 86_400],
  ['hour', 3_600],
  ['min', 60],
]

/**
 * Formats a Date, ISO string, or timestamp into a human-readable relative
 * time string like "2 mins ago" or "3 hours ago".
 * Falls back to `formatDate` for anything older than 30 days.
 */
export function formatRelativeTime(
  value: Date | string | number | null | undefined,
): string {
  if (value == null) return ''
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return ''

  const seconds = Math.floor((Date.now() - date.getTime()) / 1000)
  if (seconds < 60) return 'just now'

  for (const [unit, secs] of RELATIVE_UNITS) {
    const count = Math.floor(seconds / secs)
    if (count >= 1) {
      if (count > 30 && unit === 'day') return formatDate(value)
      return `${count} ${unit}${count > 1 ? 's' : ''} ago`
    }
  }

  return formatDate(value)
}
