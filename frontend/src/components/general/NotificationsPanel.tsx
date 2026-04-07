import { useMemo, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { Bell, Check, Loader2 } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '#/components/ui/tabs'
import { ScrollArea } from '#/components/ui/scroll-area'
import { Separator } from '#/components/ui/separator'
import { Skeleton } from '#/components/ui/skeleton'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '#/components/ui/popover'
import {
  useNotificationPolling,
  useNotifications,
  useMarkNotificationRead,
} from '#/hooks/use-notifications'
import { useWebSocketStatus } from '#/hooks/use-websocket'
import { NotificationTypeLabels } from '#/lib/models/labels'
import { NotificationTypeVariants } from '#/lib/models/badge-variants'
import { formatDate } from '#/lib/utils'
import { cn } from '#/lib/utils'
import type { NotificationItem } from '#/lib/models/types'

// ── Relative time formatter ───────────────────────────────────────────────────

function formatRelativeTime(isoString: string): string {
  const now = Date.now()
  const then = new Date(isoString).getTime()
  const diffMs = now - then
  const diffMin = Math.floor(diffMs / 60_000)
  const diffHours = Math.floor(diffMs / 3_600_000)
  const diffDays = Math.floor(diffMs / 86_400_000)

  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin} min ago`
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
  return formatDate(isoString)
}

// ── Navigation helper ─────────────────────────────────────────────────────────

function getNavigationTarget(notification: NotificationItem): string {
  const { reference_type, reference_id } = notification
  switch (reference_type) {
    case 'ASSET':
      return `/assets/${reference_id}`
    case 'ISSUE':
      return `/assets/${reference_id}?tab=issues`
    case 'SOFTWARE':
      return `/assets/${reference_id}?tab=software-requests`
    case 'DISPOSAL':
    case 'RETURN':
      return `/assets/${reference_id}`
    case 'AUDIT':
      return `/audit`
    default:
      return `/assets/${reference_id}`
  }
}

// ── Single notification row ───────────────────────────────────────────────────

function NotificationRow({
  notification,
  onMarkRead,
  onNavigate,
  isMarkingRead,
}: {
  notification: NotificationItem
  onMarkRead: (id: string) => void
  onNavigate: (notification: NotificationItem) => void
  isMarkingRead: boolean
}) {
  const variant = NotificationTypeVariants[notification.notification_type]

  return (
    <div
      className={cn(
        'flex gap-3 px-4 py-3 cursor-pointer hover:bg-muted/50 transition-colors group',
        !notification.is_read && 'bg-info-subtle/60',
      )}
      onClick={() => onNavigate(notification)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onNavigate(notification)}
    >
      {/* Unread dot */}
      <div className="mt-1.5 shrink-0 w-2 flex justify-center">
        {!notification.is_read && (
          <span className="size-2 rounded-full bg-info shrink-0" />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p
            className={cn(
              'text-sm leading-snug truncate',
              !notification.is_read ? 'font-semibold' : 'font-normal',
            )}
          >
            {notification.title}
          </p>
          <span className="text-[11px] text-muted-foreground shrink-0 mt-0.5">
            {formatRelativeTime(notification.created_at)}
          </span>
        </div>

        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
          {notification.message}
        </p>

        <div className="flex items-center justify-between mt-1.5">
          <Badge variant={variant} size="sm">
            {NotificationTypeLabels[notification.notification_type]}
          </Badge>

          {!notification.is_read && (
            <Button
              variant="ghost"
              size="icon"
              className="size-6 opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={(e) => {
                e.stopPropagation()
                onMarkRead(notification.notification_id)
              }}
              disabled={isMarkingRead}
              title="Mark as read"
            >
              <Check className="size-3" />
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Notification list (tab content) ──────────────────────────────────────────

function NotificationList({
  isReadFilter,
  onClose,
}: {
  isReadFilter: boolean | undefined
  onClose: () => void
}) {
  const navigate = useNavigate()
  const {
    data,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useNotifications(isReadFilter)
  const { mutate: markRead, isPending: isMarkingRead } =
    useMarkNotificationRead()

  const allItems = useMemo(
    () => data?.pages.flatMap((p) => p.items) ?? [],
    [data],
  )

  function handleNavigate(notification: NotificationItem) {
    if (!notification.is_read) {
      markRead(notification.notification_id)
    }
    const target = getNavigationTarget(notification)
    navigate({ to: target as never })
    onClose()
  }

  if (isLoading) {
    return (
      <div className="p-4 space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex gap-3">
            <Skeleton className="size-2 mt-2 rounded-full shrink-0" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-3.5 w-3/4" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <div className="p-6 text-center">
        <p className="text-sm text-muted-foreground">
          Failed to load notifications. Try again.
        </p>
      </div>
    )
  }

  if (allItems.length === 0) {
    return (
      <div className="p-8 text-center">
        <Bell className="size-8 text-muted-foreground/40 mx-auto mb-2" />
        <p className="text-sm text-muted-foreground">
          {isReadFilter === false
            ? 'No unread notifications'
            : 'No notifications'}
        </p>
      </div>
    )
  }

  return (
    <>
      {allItems.map((notification, idx) => (
        <div key={notification.notification_id}>
          <NotificationRow
            notification={notification}
            onMarkRead={markRead}
            onNavigate={handleNavigate}
            isMarkingRead={isMarkingRead}
          />
          {idx < allItems.length - 1 && <Separator />}
        </div>
      ))}

      {hasNextPage && (
        <div className="p-3 text-center">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => fetchNextPage()}
            disabled={isFetchingNextPage}
            className="w-full text-xs"
          >
            {isFetchingNextPage ? (
              <>
                <Loader2 className="size-3 mr-1.5 animate-spin" />
                Loading...
              </>
            ) : (
              'Load more'
            )}
          </Button>
        </div>
      )}
    </>
  )
}

// ── Main panel ────────────────────────────────────────────────────────────────

export function NotificationsPanel() {
  const [open, setOpen] = useState(false)
  const [tab, setTab] = useState<'all' | 'unread'>('all')

  const { data: unreadCount } = useNotificationPolling(open)
  const displayCount = unreadCount ?? 0
  const wsStatus = useWebSocketStatus()

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative group"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5 text-muted-foreground group-hover:text-foreground transition-colors" />
          {displayCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex size-4 items-center justify-center rounded-full bg-info text-[10px] font-bold text-white leading-none">
              {displayCount > 99 ? '99+' : displayCount}
            </span>
          )}
          {/* WebSocket connection status dot */}
          {wsStatus === 'reconnecting' && (
            <span
              className="absolute bottom-0 right-0 size-2 rounded-full bg-warning animate-pulse"
              title="Reconnecting to real-time notifications"
            />
          )}
          {wsStatus === 'disconnected' && (
            <span
              className="absolute bottom-0 right-0 size-2 rounded-full bg-danger"
              title="Real-time notifications unavailable"
            />
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent align="end" sideOffset={8} className="w-96 p-0 shadow-lg">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold">Notifications</p>
            {displayCount > 0 && (
              <Badge variant="info" size="sm">
                {displayCount} unread
              </Badge>
            )}
          </div>
        </div>

        {/* Tabs */}
        <Tabs
          value={tab}
          onValueChange={(v) => setTab(v as 'all' | 'unread')}
          className="gap-0"
        >
          <TabsList variant="line" className="px-4 border-b w-full">
            <TabsTrigger value="all" className="text-xs px-3">
              All
            </TabsTrigger>
            <TabsTrigger value="unread" className="text-xs px-3">
              Unread
            </TabsTrigger>
          </TabsList>
          <TabsContent value="all">
            <ScrollArea className="max-h-96 overflow-y-auto">
              <NotificationList
                isReadFilter={undefined}
                onClose={() => setOpen(false)}
              />
            </ScrollArea>
          </TabsContent>

          <TabsContent value="unread">
            <ScrollArea className="max-h-96 overflow-y-auto">
              <NotificationList
                isReadFilter={false}
                onClose={() => setOpen(false)}
              />
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </PopoverContent>
    </Popover>
  )
}
