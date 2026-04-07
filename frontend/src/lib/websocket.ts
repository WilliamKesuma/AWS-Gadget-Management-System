import { fetchAuthSession } from 'aws-amplify/auth'
import type { WebSocketMessage, WebSocketNotificationPayload } from './models/types'

const WS_ENDPOINT = import.meta.env.VITE_WS_ENDPOINT?.trim()

type NotificationListener = (payload: WebSocketNotificationPayload) => void
type StatusListener = (status: ConnectionStatus) => void

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting'

const BACKOFF_BASE = 1000
const BACKOFF_MAX = 30_000
const RAPID_WINDOW_MS = 5_000
const RAPID_THRESHOLD = 3

class WebSocketManager {
    private ws: WebSocket | null = null
    private status: ConnectionStatus = 'disconnected'
    private retryCount = 0
    private retryTimer: ReturnType<typeof setTimeout> | null = null
    private intentionalClose = false

    private notificationListeners = new Set<NotificationListener>()
    private statusListeners = new Set<StatusListener>()

    // Rapid notification batching
    private recentTimestamps: number[] = []

    // ── Public API ────────────────────────────────────────────────────────────

    async connect() {
        if (!WS_ENDPOINT) {
            console.warn('VITE_WS_ENDPOINT not configured — WebSocket disabled')
            return
        }
        if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
            return
        }
        this.intentionalClose = false
        await this.open()
    }

    disconnect() {
        this.intentionalClose = true
        this.clearRetryTimer()
        if (this.ws) {
            this.ws.close()
            this.ws = null
        }
        this.setStatus('disconnected')
        this.retryCount = 0
    }

    onNotification(listener: NotificationListener): () => void {
        this.notificationListeners.add(listener)
        return () => this.notificationListeners.delete(listener)
    }

    onStatusChange(listener: StatusListener): () => void {
        this.statusListeners.add(listener)
        listener(this.status)
        return () => this.statusListeners.delete(listener)
    }

    getStatus(): ConnectionStatus {
        return this.status
    }

    /**
     * Returns true if more than RAPID_THRESHOLD notifications arrived
     * within the last RAPID_WINDOW_MS. Used by the UI to batch toasts.
     */
    isRapidBurst(): boolean {
        const now = Date.now()
        this.recentTimestamps = this.recentTimestamps.filter((t) => now - t < RAPID_WINDOW_MS)
        return this.recentTimestamps.length > RAPID_THRESHOLD
    }

    // ── Internals ─────────────────────────────────────────────────────────────

    private async getIdToken(): Promise<string | null> {
        try {
            const session = await fetchAuthSession()
            return session.tokens?.idToken?.toString() ?? null
        } catch {
            return null
        }
    }

    private async open() {
        const token = await this.getIdToken()
        if (!token) {
            console.warn('No Cognito ID token — cannot open WebSocket')
            this.setStatus('disconnected')
            return
        }

        this.setStatus(this.retryCount > 0 ? 'reconnecting' : 'connecting')

        try {
            this.ws = new WebSocket(`${WS_ENDPOINT}?token=${token}`)
        } catch {
            this.scheduleReconnect()
            return
        }

        this.ws.onopen = () => {
            this.retryCount = 0
            this.setStatus('connected')
        }

        this.ws.onmessage = (event) => {
            try {
                const message: WebSocketMessage = JSON.parse(event.data)
                if (message.type === 'notification') {
                    this.recentTimestamps.push(Date.now())
                    for (const listener of this.notificationListeners) {
                        listener(message.data)
                    }
                }
            } catch {
                // Ignore malformed messages
            }
        }

        this.ws.onclose = () => {
            this.ws = null
            if (!this.intentionalClose) {
                this.setStatus('reconnecting')
                this.scheduleReconnect()
            }
        }

        this.ws.onerror = () => {
            // onclose will fire after onerror — reconnect handled there
        }
    }

    private scheduleReconnect() {
        this.clearRetryTimer()
        const delay = Math.min(BACKOFF_BASE * 2 ** this.retryCount, BACKOFF_MAX)
        this.retryCount++
        this.retryTimer = setTimeout(() => {
            if (!this.intentionalClose) {
                void this.open()
            }
        }, delay)
    }

    private clearRetryTimer() {
        if (this.retryTimer) {
            clearTimeout(this.retryTimer)
            this.retryTimer = null
        }
    }

    private setStatus(next: ConnectionStatus) {
        if (this.status === next) return
        this.status = next
        for (const listener of this.statusListeners) {
            listener(next)
        }
    }
}

/** Singleton WebSocket manager — shared across the app */
export const wsManager = new WebSocketManager()
