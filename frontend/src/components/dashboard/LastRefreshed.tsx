import { useState, useEffect } from 'react'
import { RefreshCw } from 'lucide-react'
import { formatRelativeTime } from '#/lib/utils'

interface LastRefreshedProps {
  dataUpdatedAt: number | undefined
}

export function LastRefreshed({ dataUpdatedAt }: LastRefreshedProps) {
  const [, setTick] = useState(0)

  // Re-render every 30s so the relative time stays fresh
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 30_000)
    return () => clearInterval(id)
  }, [])

  if (!dataUpdatedAt) return null

  return (
    <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <RefreshCw className="size-3" />
      Last updated {formatRelativeTime(dataUpdatedAt)}
    </span>
  )
}
