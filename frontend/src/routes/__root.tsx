import {
  HeadContent,
  Outlet,
  createRootRouteWithContext,
} from '@tanstack/react-router'
import TanStackQueryProvider from '../integrations/tanstack-query/root-provider'
import '../lib/auth'
import type { QueryClient } from '@tanstack/react-query'
import type { UserRole } from '#/lib/models/types'
import '../styles.css'
import { ErrorPage } from '#/components/errors/ErrorPage'
import { NotFoundPage } from '#/components/errors/NotFoundPage'
import { Toaster } from '#/components/ui/sonner'
import { TooltipProvider } from '#/components/ui/tooltip'
import { ThemeProvider } from 'next-themes'

export interface UserAttributes {
  email?: string
  name?: string
  given_name?: string
  family_name?: string
  [key: string]: string | undefined
}

interface MyRouterContext {
  queryClient: QueryClient
  userId: string | null
  userRole: UserRole | null
  userAttributes: UserAttributes | null
}

export const Route = createRootRouteWithContext<MyRouterContext>()({
  component: RootComponent,
  errorComponent: ErrorPage,
  notFoundComponent: NotFoundPage,
})

function RootComponent() {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
      <HeadContent />
      <TooltipProvider>
        <TanStackQueryProvider>
          <Outlet />
        </TanStackQueryProvider>
      </TooltipProvider>
      <Toaster position="top-right" richColors />
    </ThemeProvider>
  )
}
