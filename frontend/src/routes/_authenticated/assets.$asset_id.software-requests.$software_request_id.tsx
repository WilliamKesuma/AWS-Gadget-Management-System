import { lazy, Suspense } from 'react'
import { createFileRoute, redirect } from '@tanstack/react-router'
import type { UserRole } from '#/lib/models/types'
import {
  getBaseMeta,
  getPageMeta,
  getCanonicalLink,
  type SeoPageInput,
} from '../../lib/seo'
import { hasRole } from '#/lib/permissions'
import { Skeleton } from '#/components/ui/skeleton'

const SoftwareRequestDetail = lazy(() =>
  import('#/components/software/SoftwareRequestDetail').then((m) => ({
    default: m.SoftwareRequestDetail,
  })),
)

const SOFTWARE_REQUEST_DETAIL_SEO = {
  title: 'Software Request Detail',
  description:
    'View full details of a software installation request including status, risk assessment, and review history.',
  path: '/assets/software-requests/detail',
} satisfies SeoPageInput

const ALLOWED = ['it-admin', 'management', 'employee'] as const

export const Route = createFileRoute(
  '/_authenticated/assets/$asset_id/software-requests/$software_request_id' as any,
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
  component: SoftwareRequestDetailPage,
  head: () => ({
    meta: [
      ...getBaseMeta(),
      { name: 'robots', content: 'noindex, nofollow' },
      ...getPageMeta(SOFTWARE_REQUEST_DETAIL_SEO),
    ],
    links: [getCanonicalLink(SOFTWARE_REQUEST_DETAIL_SEO.path)],
  }),
})

function SoftwareRequestDetailPage() {
  const { asset_id, software_request_id } = Route.useParams() as {
    asset_id: string
    software_request_id: string
  }

  return (
    <main className="page-base">
      <Suspense fallback={<Skeleton className="h-96 w-full rounded-xl" />}>
        <SoftwareRequestDetail
          assetId={asset_id}
          softwareRequestId={software_request_id}
        />
      </Suspense>
    </main>
  )
}
