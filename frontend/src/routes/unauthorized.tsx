import { createFileRoute } from '@tanstack/react-router'
import { UnauthorizedPage } from '#/components/errors/UnauthorizedPage'
import { getBaseMeta, getPageMeta, getCanonicalLink } from '../lib/seo'
import type { SeoPageInput } from '../lib/seo'

const UNAUTHORIZED_SEO = {
  title: 'Access Denied',
  description:
    'You do not have permission to access this page. Contact your administrator if you believe this is a mistake.',
  path: '/unauthorized',
} satisfies SeoPageInput

export const Route = createFileRoute('/unauthorized')({
  component: UnauthorizedPage,
  head: () => ({
    meta: [
      ...getBaseMeta(),
      { name: 'robots', content: 'noindex, nofollow' },
      ...getPageMeta(UNAUTHORIZED_SEO),
    ],
    links: [getCanonicalLink(UNAUTHORIZED_SEO.path)],
  }),
})
