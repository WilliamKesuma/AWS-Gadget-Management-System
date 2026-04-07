import { useRouterState } from '@tanstack/react-router'
import type { UserRole } from '#/lib/models/types'
import type { UserAttributes } from '#/routes/__root'

export function useCurrentUserId(): string | null {
  return useRouterState({
    select: (s) => {
      for (const m of s.matches) {
        const ctx = m.context as Record<string, unknown> | undefined
        if (ctx && 'userId' in ctx && ctx.userId != null) {
          return ctx.userId as string
        }
      }
      return null
    },
  })
}

export function useCurrentUserRole(): UserRole | null {
  return useRouterState({
    select: (s) => {
      for (const m of s.matches) {
        const ctx = m.context as Record<string, unknown> | undefined
        if (ctx && 'userRole' in ctx && ctx.userRole != null) {
          return ctx.userRole as UserRole
        }
      }
      return null
    },
  })
}

export function useCurrentUserAttributes(): UserAttributes | null {
  return useRouterState({
    select: (s) => {
      for (const m of s.matches) {
        const ctx = m.context as Record<string, unknown> | undefined
        if (ctx && 'userAttributes' in ctx && ctx.userAttributes != null) {
          return ctx.userAttributes as UserAttributes
        }
      }
      return null
    },
  })
}
