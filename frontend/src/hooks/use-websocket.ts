import { useEffect, useSyncExternalStore, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { wsManager, type ConnectionStatus } from '#/lib/websocket'
import { queryKeys } from '#/lib/query-keys'

// ── Connection status hook ────────────────────────────────────────────────────

export function useWebSocketStatus(): ConnectionStatus {
    const subscribe = useCallback(
        (cb: () => void) => wsManager.onStatusChange(cb),
        [],
    )
    const getSnapshot = useCallback(() => wsManager.getStatus(), [])
    return useSyncExternalStore(subscribe, getSnapshot, getSnapshot)
}

// ── Main hook — mount once in _authenticated layout ───────────────────────────

export function useWebSocket() {
    const queryClient = useQueryClient()

    // Connect on mount, disconnect on unmount (logout navigates away from _authenticated)
    useEffect(() => {
        wsManager.connect()
        return () => wsManager.disconnect()
    }, [])

    // Reconnect with fresh token when window regains focus after being hidden
    useEffect(() => {
        function handleVisibility() {
            if (document.visibilityState === 'visible' && wsManager.getStatus() !== 'connected') {
                wsManager.connect()
            }
        }
        document.addEventListener('visibilitychange', handleVisibility)
        return () => document.removeEventListener('visibilitychange', handleVisibility)
    }, [])

    // Handle incoming notifications
    useEffect(() => {
        return wsManager.onNotification(() => {
            // Increment unread count
            queryClient.setQueryData(
                queryKeys.notifications.unreadCount(),
                (old: number | undefined) => (old ?? 0) + 1,
            )

            // Invalidate notification lists so next open gets fresh data
            queryClient.invalidateQueries({
                queryKey: queryKeys.notifications.list({}),
            })
            queryClient.invalidateQueries({
                queryKey: queryKeys.notifications.list({ is_read: false }),
            })
        })
    }, [queryClient])
}
