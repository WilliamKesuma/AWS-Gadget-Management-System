import { lazy, Suspense } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import {
  getBaseMeta,
  getPageMeta,
  getCanonicalLink,
  type SeoPageInput,
} from '../../lib/seo'
import { useCurrentUserRole } from '#/hooks/use-current-user'
import { Skeleton } from '#/components/ui/skeleton'

const EmployeeDashboard = lazy(
  () =>
    import('#/components/dashboard/EmployeeDashboard').then((m) => ({
      default: m.EmployeeDashboard,
    })),
)
const FinanceDashboard = lazy(
  () =>
    import('#/components/dashboard/FinanceDashboard').then((m) => ({
      default: m.FinanceDashboard,
    })),
)
const ITAdminDashboard = lazy(
  () =>
    import('#/components/dashboard/ITAdminDashboard').then((m) => ({
      default: m.ITAdminDashboard,
    })),
)
const ManagementDashboard = lazy(
  () =>
    import('#/components/dashboard/ManagementDashboard').then((m) => ({
      default: m.ManagementDashboard,
    })),
)

const DASHBOARD_SEO = {
  title: 'Overview Dashboard',
  description:
    'Monitor real-time hardware health, track pending support tickets, and get a complete overview of the Gadget Management System.',
  path: '/',
} satisfies SeoPageInput

export const Route = createFileRoute('/_authenticated/')({
  component: DashboardPage,
  head: () => ({
    meta: [
      ...getBaseMeta(),
      { name: 'robots', content: 'noindex, nofollow' },
      ...getPageMeta(DASHBOARD_SEO),
    ],
    links: [getCanonicalLink(DASHBOARD_SEO.path)],
  }),
})

function DashboardFallback() {
  return (
    <main className="page-base">
      <div className="space-y-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="rounded-xl border bg-card p-6 space-y-3">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-16" />
          </div>
        ))}
      </div>
    </main>
  )
}

function DashboardPage() {
  const role = useCurrentUserRole()

  const Dashboard = (() => {
    switch (role) {
      case 'employee':
        return EmployeeDashboard
      case 'finance':
        return FinanceDashboard
      case 'it-admin':
        return ITAdminDashboard
      case 'management':
        return ManagementDashboard
      default:
        return ITAdminDashboard
    }
  })()

  return (
    <Suspense fallback={<DashboardFallback />}>
      <Dashboard />
    </Suspense>
  )
}
