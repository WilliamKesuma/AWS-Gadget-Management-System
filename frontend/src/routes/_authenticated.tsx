import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'
import { Header } from '#/components/general/Header'
import { ErrorPage } from '#/components/errors/ErrorPage'
import { NotFoundPage } from '#/components/errors/NotFoundPage'
import { getAuthSession } from '../lib/auth'
import { useWebSocket } from '#/hooks/use-websocket'

export const Route = createFileRoute('/_authenticated')({
  beforeLoad: async ({ location }) => {
    const session = await getAuthSession()
    if (!session) {
      throw redirect({
        to: '/login',
        search: {
          redirectTo: location.href,
        },
      })
    }
    return {
      userId: session.userId,
      userRole: session.userRole,
      userAttributes: session.userAttributes,
    }
  },
  component: AuthenticatedLayout,
  errorComponent: ErrorPage,
  notFoundComponent: NotFoundPage,
})

function AuthenticatedLayout() {
  useWebSocket()

  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[100] focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground focus:text-sm focus:font-medium"
      >
        Skip to main content
      </a>
      <Header />
      <div id="main-content">
        <Outlet />
      </div>
    </>
  )
}
