import {
  createFileRoute,
  redirect,
  useNavigate,
  useRouterState,
} from '@tanstack/react-router'
import { z } from 'zod'
import { useState } from 'react'
import {
  getBaseMeta,
  getPageMeta,
  getCanonicalLink,
  type SeoPageInput,
} from '../../lib/seo'
import { ConfirmAssetForm } from '#/components/assets/ConfirmAssetForm'
import { UploadAssetModal } from '#/components/assets/UploadAssetModal'
import type { ExtractedFieldValue, UserRole } from '#/lib/models/types'
import { hasRole } from '#/lib/permissions'

// ─── Search schema ────────────────────────────────────────────────────────────

const searchSchema = z.object({
  upload_session_id: z.string().optional(),
  scan_job_id: z.string().optional(),
  ready: z.coerce.number().optional(),
  asset_id: z.string().optional(),
})

type AssetNewSearch = z.infer<typeof searchSchema>

// ─── SEO ──────────────────────────────────────────────────────────────────────

const ASSET_NEW_SEO = {
  title: 'Create Asset',
  description:
    'Review AI-extracted asset details, confirm field values, and submit the asset for management approval.',
  path: '/assets/new',
} satisfies SeoPageInput

// ─── Route ────────────────────────────────────────────────────────────────────

export const Route = createFileRoute('/_authenticated/assets/new' as any)({
  validateSearch: (raw: Record<string, unknown>): AssetNewSearch =>
    searchSchema.parse(raw),
  beforeLoad: ({ context }) => {
    if (
      !hasRole((context as { userRole?: UserRole | null }).userRole ?? null, [
        'it-admin',
      ])
    ) {
      throw redirect({ to: '/unauthorized' })
    }
  },
  component: AssetCreationWizard,
  head: () => ({
    meta: [
      ...getBaseMeta(),
      { name: 'robots', content: 'noindex, nofollow' },
      ...getPageMeta(ASSET_NEW_SEO),
    ],
    links: [getCanonicalLink(ASSET_NEW_SEO.path)],
  }),
})

// ─── AssetCreationWizard ──────────────────────────────────────────────────────

function AssetCreationWizard() {
  const navigate = useNavigate()
  const { asset_id, scan_job_id, ready, upload_session_id } =
    Route.useSearch() as AssetNewSearch
  const routerState = useRouterState({ select: (s) => s.location.state })
  const extractedFields = (routerState as any)?.extracted_fields as
    | Record<string, ExtractedFieldValue>
    | undefined

  const [uploadOpen, setUploadOpen] = useState(!scan_job_id && !asset_id)

  function handleClose() {
    void navigate({ to: '/assets', search: {} })
  }

  // Upload+polling modal — shown when no scan result yet
  if (!scan_job_id && !asset_id) {
    return (
      <UploadAssetModal
        open={uploadOpen}
        onOpenChange={(open) => {
          setUploadOpen(open)
          if (!open) handleClose()
        }}
      />
    )
  }

  const isSuccess = !!asset_id
  const isConfirm = !!scan_job_id && ready === 1

  if (!isSuccess && !isConfirm) {
    handleClose()
    return null
  }

  return (
    <ConfirmAssetForm
      open
      onOpenChange={(open) => !open && handleClose()}
      scanJobId={scan_job_id ?? ''}
      uploadSessionId={upload_session_id ?? ''}
      extractedFields={extractedFields}
      successAssetId={asset_id}
    />
  )
}
