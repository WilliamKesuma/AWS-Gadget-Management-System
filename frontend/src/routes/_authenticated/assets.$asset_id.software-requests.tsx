import { createFileRoute, redirect, Outlet } from '@tanstack/react-router'
import type { UserRole } from '#/lib/models/types'
import {
  getBaseMeta,
  getPageMeta,
  getCanonicalLink,
  type SeoPageInput,
} from '../../lib/seo'
import { hasRole } from '#/lib/permissions'

const SOFTWARE_REQUESTS_SEO = {
  title: 'Software Requests',
  description:
    'View and manage software installation requests for this asset, track approval status and review history.',
  path: '/assets/software-requests',
} satisfies SeoPageInput

const ALLOWED = ['it-admin', 'employee', 'management'] as const

export const Route = createFileRoute(
  '/_authenticated/assets/$asset_id/software-requests' as any,
)({
  beforeLoad: ({ context }) => {
    if (
      !hasRole((context as { userRole?: UserRole | null }).userRole ?? null, [
        ...ALLOWED,
      ])
    ) {
      throw redirect({ to: '/unauthorized' })
    }
  },
  component: () => <Outlet />,
  head: () => ({
    meta: [
      ...getBaseMeta(),
      { name: 'robots', content: 'noindex, nofollow' },
      ...getPageMeta(SOFTWARE_REQUESTS_SEO),
    ],
    links: [getCanonicalLink(SOFTWARE_REQUESTS_SEO.path)],
  }),
})
