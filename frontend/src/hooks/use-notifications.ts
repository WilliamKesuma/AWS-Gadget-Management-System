import {
  useQuery,
  useMutation,
  useQueryClient,
  useInfiniteQuery,
} from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiClient, ApiError } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type {
  ListNotificationsResponse,
  MarkNotificationReadResponse,
  NotificationItem,
} from '#/lib/models/types'

// ── Unread count (fetched once, then updated via WebSocket) ───────────────────

export function useNotificationUnreadCount() {
  return useQuery({
    queryKey: queryKeys.notifications.unreadCount(),
    queryFn: async () => {
      const res = await apiClient<ListNotificationsResponse>(
        '/notifications',
      )
      return res.unread_count
    },
    staleTime: Infinity,
  })
}

// ── Paginated notifications list ──────────────────────────────────────────────

export function useNotifications(isReadFilter: boolean | undefined) {
  const baseParams = new URLSearchParams()
  if (isReadFilter !== undefined) {
    baseParams.set('is_read', String(isReadFilter))
  }

  return useInfiniteQuery({
    queryKey: queryKeys.notifications.list({
      is_read: isReadFilter,
    }),
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams(baseParams)
      if (pageParam) {
        params.set('cursor', pageParam)
      }
      return apiClient<ListNotificationsResponse>(
        `/notifications?${params.toString()}`,
      )
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => {
      if (lastPage.has_next_page && lastPage.next_cursor) {
        return lastPage.next_cursor
      }
      return undefined
    },
    staleTime: 60_000,
  })
}

// ── Mark as read mutation ─────────────────────────────────────────────────────

export function useMarkNotificationRead() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['notifications', 'mark-read'],
    mutationFn: (notificationId: string) =>
      apiClient<MarkNotificationReadResponse>(
        `/notifications/${notificationId}`,
        { method: 'PATCH' },
      ),
    onMutate: async (notificationId) => {
      const listKeys = queryClient
        .getQueryCache()
        .findAll({ queryKey: queryKeys.notifications.all() })

      for (const query of listKeys) {
        queryClient.setQueryData(query.queryKey, (old: unknown) => {
          if (!old || typeof old !== 'object') return old
          const data = old as {
            pages: { items: NotificationItem[]; unread_count: number }[]
          }
          return {
            ...data,
            pages: data.pages.map((page) => ({
              ...page,
              unread_count: Math.max(0, page.unread_count - 1),
              items: page.items.map((n) =>
                n.notification_id === notificationId
                  ? { ...n, is_read: true }
                  : n,
              ),
            })),
          }
        })
      }

      queryClient.setQueryData(
        queryKeys.notifications.unreadCount(),
        (old: number | undefined) =>
          old !== undefined ? Math.max(0, old - 1) : old,
      )
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        toast.error(err.message)
      } else {
        toast.error('Failed to mark notification as read.')
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all() })
    },
  })
}

// ── Unread count hook (no polling — WebSocket drives updates) ─────────────────

export function useNotificationPolling(_isPanelOpen: boolean) {
  return useNotificationUnreadCount()
}
