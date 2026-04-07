import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Hub } from 'aws-amplify/utils'
import { ApiError } from '../../lib/api-client'

import type { UserRole } from '../../lib/models/types'
import type { UserAttributes } from '../../routes/__root'

let context:
  | {
      queryClient: QueryClient
      userId: string | null
      userRole: UserRole | null
      userAttributes: UserAttributes | null
    }
  | undefined

export function getContext() {
  if (context) {
    return context
  }

  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: (failureCount, error) => {
          // Don't retry on 403 Forbidden
          if (error instanceof ApiError && error.status === 403) {
            return false
          }
          // Default: retry up to 3 times
          return failureCount < 3
        },
      },
    },
  })

  // Clear the cache whenever the auth state changes (Amplify-wide)
  Hub.listen('auth', ({ payload }) => {
    if (payload.event === 'signedIn' || payload.event === 'signedOut') {
      queryClient.clear()
    }
  })

  context = {
    queryClient,
    userId: null,
    userRole: null,
    userAttributes: null,
  }

  return context
}

import type { ReactNode } from 'react'

export default function TanStackQueryProvider({
  children,
}: {
  children: ReactNode
}) {
  const { queryClient } = getContext()

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}
