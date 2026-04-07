import { lazy, Suspense, useState, useCallback } from 'react'
import {
  createFileRoute,
  redirect,
  Link,
  useNavigate,
} from '@tanstack/react-router'
import { useQueryClient } from '@tanstack/react-query'
import {
  Camera,
  User,
  Calendar,
  RotateCcw,
  RefreshCw,
  Check,
  PenLine,
  ImageIcon,
} from 'lucide-react'
import type { UserRole, ReturnStatus } from '#/lib/models/types'
import {
  getBaseMeta,
  getPageMeta,
  getCanonicalLink,
  type SeoPageInput,
} from '../../lib/seo'
import { useReturnDetail } from '#/hooks/use-returns'
import {
  useSubmitAdminEvidence,
  useGenerateReturnUploadUrls,
} from '#/hooks/use-returns'
import { useCurrentUserRole } from '#/hooks/use-current-user'
import { getReturnDetailPermissions } from '#/lib/permissions'
import { hasRole } from '#/lib/permissions'
import { formatDate, cn } from '#/lib/utils'
import { toast } from 'sonner'
import { Skeleton } from '#/components/ui/skeleton'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'
import { Card, CardHeader, CardTitle, CardContent } from '#/components/ui/card'
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbSeparator,
  BreadcrumbPage,
} from '#/components/ui/breadcrumb'
import { ReturnConditionBadge } from '#/components/returns/ReturnConditionBadge'
import { ResetStatusBadge } from '#/components/returns/ResetStatusBadge'
import { ReturnTriggerDisplay } from '#/components/returns/ReturnTriggerDisplay'
import { EvidencePhotoGrid } from '#/components/returns/EvidencePhotoGrid'
import { DragDropZone } from '#/components/assets/DragDropZone'
import { SignatureCapture } from '#/components/assets/SignatureCapture'
import { ReturnStatusBadge } from '#/components/returns/ReturnStatusBadge'
import { AssetStatusLabels } from '#/lib/models/labels'

// Lazy-loaded dialog
const EmployeeSignatureDialog = lazy(() =>
  import('#/components/returns/EmployeeSignatureDialog').then((m) => ({
    default: m.EmployeeSignatureDialog,
  })),
)
import { AssetStatusVariants } from '#/lib/models/badge-variants'
import { queryKeys } from '#/lib/query-keys'

// ── SEO ───────────────────────────────────────────────────────────────────────

const RETURN_DETAIL_SEO = {
  title: 'Return Detail',
  description:
    'View full asset return details including condition assessment, evidence photos, and signature records.',
  path: '/assets/returns/detail',
} satisfies SeoPageInput

// ── Route config ──────────────────────────────────────────────────────────────

const ALLOWED: UserRole[] = ['it-admin', 'employee']

export const Route = createFileRoute(
  '/_authenticated/assets/$asset_id/returns/$return_id' as any,
)({
  beforeLoad: ({ context }) => {
    if (
      !hasRole(
        (context as { userRole?: UserRole | null }).userRole ?? null,
        ALLOWED,
      )
    ) {
      throw redirect({ to: '/unauthorized' })
    }
  },
  component: ReturnDetailPage,
  head: () => ({
    meta: [
      ...getBaseMeta(),
      { name: 'robots', content: 'noindex, nofollow' },
      ...getPageMeta(RETURN_DETAIL_SEO),
    ],
    links: [getCanonicalLink(RETURN_DETAIL_SEO.path)],
  }),
})

// ── Component ─────────────────────────────────────────────────────────────────

function ReturnDetailPage() {
  const { asset_id, return_id } = Route.useParams() as {
    asset_id: string
    return_id: string
  }
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const role = useCurrentUserRole()
  const {
    data: returnData,
    isLoading,
    error,
  } = useReturnDetail(asset_id, return_id)

  const [employeeSignatureOpen, setEmployeeSignatureOpen] = useState(false)
  const [pendingPhotos, setPendingPhotos] = useState<File[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [isUploadingSignature, setIsUploadingSignature] = useState(false)

  const renotifyMutation = useSubmitAdminEvidence(asset_id)
  const generateUrlsMutation = useGenerateReturnUploadUrls(asset_id)

  const permissions = returnData
    ? getReturnDetailPermissions({
      role,
      assetStatus: returnData.asset_status,
      adminSignatureUrl: returnData.admin_signature_url,
      userSignatureUrl: returnData.user_signature_url,
    })
    : null

  function handleRenotify() {
    renotifyMutation.mutate(return_id, {
      onSuccess: () => {
        toast.success(
          'Employee has been re-notified to provide their signature.',
        )
      },
      onError: (err) => {
        toast.error((err as Error).message || 'Failed to re-notify employee.')
      },
    })
  }

  const handleUploadPhotos = useCallback(async () => {
    if (pendingPhotos.length === 0) return
    setIsUploading(true)
    try {
      const manifest = pendingPhotos.map((f) => ({
        name: f.name,
        type: 'photo' as const,
        content_type: f.type || 'image/jpeg',
      }))

      const { upload_urls } = await generateUrlsMutation.mutateAsync({
        returnId: return_id,
        files: manifest,
      })

      for (let i = 0; i < pendingPhotos.length; i++) {
        const url = upload_urls[i]
        if (!url) throw new Error('Missing presigned URL.')
        const res = await fetch(url.presigned_url, {
          method: 'PUT',
          body: pendingPhotos[i],
          headers: { 'Content-Type': url.content_type },
        })
        if (!res.ok) {
          toast.error(
            res.status === 403
              ? 'Upload session expired. Please try again.'
              : 'One or more files failed to upload. Please try again.',
          )
          setIsUploading(false)
          return
        }
      }

      setPendingPhotos([])
      toast.success('Photos uploaded successfully.')
      void queryClient.invalidateQueries({
        queryKey: queryKeys.returns.detail(asset_id, return_id),
      })
    } catch (err) {
      toast.error(
        (err as Error).message || 'Failed to upload photos. Please try again.',
      )
    } finally {
      setIsUploading(false)
    }
  }, [pendingPhotos, asset_id, return_id, generateUrlsMutation, queryClient])

  const handleUploadSignature = useCallback(
    async (blob: Blob) => {
      setIsUploadingSignature(true)
      try {
        const { upload_urls } = await generateUrlsMutation.mutateAsync({
          returnId: return_id,
          files: [
            {
              name: 'admin-signature.png',
              type: 'admin-signature' as const,
              content_type: 'image/png',
            },
          ],
        })

        const sigUrl = upload_urls.find((u) => u.type === 'admin-signature')
        if (!sigUrl) throw new Error('No signature URL returned.')

        const res = await fetch(sigUrl.presigned_url, {
          method: 'PUT',
          body: blob,
          headers: { 'Content-Type': sigUrl.content_type },
        })
        if (!res.ok) {
          toast.error(
            res.status === 403
              ? 'Upload session expired. Please try again.'
              : 'Signature upload failed. Please try again.',
          )
          return
        }

        toast.success('Admin signature uploaded successfully.')
        void queryClient.invalidateQueries({
          queryKey: queryKeys.returns.detail(asset_id, return_id),
        })
      } catch (err) {
        toast.error(
          (err as Error).message ||
          'Failed to upload signature. Please try again.',
        )
      } finally {
        setIsUploadingSignature(false)
      }
    },
    [asset_id, return_id, generateUrlsMutation, queryClient],
  )

  return (
    <main className="page-base">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link to="/assets">Assets</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link to="/assets/$asset_id" params={{ asset_id }}>
                {asset_id}
              </Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>Return Detail</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      {isLoading && <ReturnDetailSkeleton />}

      {error && (
        <div className="alert-danger mt-4">{(error as Error).message}</div>
      )}

      {returnData && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
          {/* Left column */}
          <div className="lg:col-span-2 space-y-6">
            {/* Return Info */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-wider flex items-center gap-2">
                  <RotateCcw className="size-4" />
                  Return Info
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-xs font-semibold text-muted-foreground mb-2">
                    Return Trigger
                  </p>
                  <ReturnTriggerDisplay trigger={returnData.return_trigger} />
                </div>
                <dl className="grid grid-cols-2 gap-4">
                  <DetailItem
                    label="Initiated By"
                    value={returnData.initiated_by}
                  />
                  <DetailItem
                    label="Initiated At"
                    value={formatDate(returnData.initiated_at) || '—'}
                  />
                  {returnData.completed_at && (
                    <DetailItem
                      label="Completed At"
                      value={formatDate(returnData.completed_at) || '—'}
                    />
                  )}
                  {returnData.completed_by && (
                    <DetailItem
                      label="Completed By"
                      value={returnData.completed_by}
                    />
                  )}
                </dl>
              </CardContent>
            </Card>

            {/* Device Info */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-wider">
                  Device Info
                </CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="grid grid-cols-2 gap-4">
                  <DetailItem label="Model" value={returnData.model || '—'} />
                  <DetailItem
                    label="Serial Number"
                    value={returnData.serial_number || '—'}
                  />
                </dl>
              </CardContent>
            </Card>

            {/* Condition Assessment */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-wider">
                  Condition Assessment
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-semibold text-muted-foreground">
                    Condition
                  </span>
                  <ReturnConditionBadge
                    condition={returnData.condition_assessment}
                  />
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-semibold text-muted-foreground">
                    Factory Reset
                  </span>
                  <ResetStatusBadge status={returnData.reset_status} />
                </div>
                {returnData.remarks && (
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground mb-1">
                      Remarks
                    </p>
                    <p className="text-sm bg-muted/30 rounded-lg p-3">
                      {returnData.remarks}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Admin Evidence */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-wider flex items-center gap-2">
                  <Camera className="size-4" />
                  Admin Evidence
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Step 1: Admin Signature */}
                <div className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div
                      className={cn(
                        'flex size-8 shrink-0 items-center justify-center rounded-full border-2 text-sm font-semibold',
                        returnData.admin_signature_url
                          ? 'border-primary bg-primary text-primary-foreground'
                          : 'border-primary bg-background text-primary',
                      )}
                    >
                      {returnData.admin_signature_url ? (
                        <Check className="size-4" />
                      ) : (
                        <PenLine className="size-4" />
                      )}
                    </div>
                    <div
                      className={cn(
                        'mt-2 w-0.5 flex-1',
                        returnData.admin_signature_url
                          ? 'bg-primary'
                          : 'bg-border',
                      )}
                    />
                  </div>
                  <div className="flex-1 pb-6">
                    <p className="text-sm font-semibold mb-1">
                      Admin Signature
                    </p>
                    <p className="text-xs text-muted-foreground mb-3">
                      {returnData.admin_signature_url
                        ? 'Signature has been provided.'
                        : 'Provide your signature to proceed to evidence upload.'}
                    </p>
                    {returnData.admin_signature_url ? (
                      <img
                        src={returnData.admin_signature_url}
                        alt="Admin signature"
                        className="h-24 border rounded-lg bg-white object-contain p-2"
                      />
                    ) : permissions?.canUploadEvidence ? (
                      <SignatureCapture
                        onSignatureReady={(blob) =>
                          void handleUploadSignature(blob)
                        }
                        disabled={isUploadingSignature}
                      />
                    ) : (
                      <p className="text-sm text-muted-foreground italic">
                        Not yet uploaded.
                      </p>
                    )}
                  </div>
                </div>

                {/* Step 2: Evidence Photos */}
                <div className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div
                      className={cn(
                        'flex size-8 shrink-0 items-center justify-center rounded-full border-2 text-sm font-semibold',
                        !returnData.admin_signature_url
                          ? 'border-muted bg-muted text-muted-foreground'
                          : returnData.return_photo_urls &&
                            returnData.return_photo_urls.length > 0
                            ? 'border-primary bg-primary text-primary-foreground'
                            : 'border-primary bg-background text-primary',
                      )}
                    >
                      {returnData.return_photo_urls &&
                        returnData.return_photo_urls.length > 0 ? (
                        <Check className="size-4" />
                      ) : (
                        <ImageIcon className="size-4" />
                      )}
                    </div>
                  </div>
                  <div className="flex-1">
                    <p
                      className={cn(
                        'text-sm font-semibold mb-1',
                        !returnData.admin_signature_url &&
                        'text-muted-foreground',
                      )}
                    >
                      Evidence Photos
                    </p>
                    <p className="text-xs text-muted-foreground mb-3">
                      {!returnData.admin_signature_url
                        ? 'Complete the signature step first.'
                        : returnData.return_photo_urls &&
                          returnData.return_photo_urls.length > 0
                          ? 'Evidence photos have been uploaded.'
                          : 'Upload photos documenting the asset condition.'}
                    </p>
                    {returnData.admin_signature_url && (
                      <>
                        {returnData.return_photo_urls &&
                          returnData.return_photo_urls.length > 0 && (
                            <EvidencePhotoGrid
                              mode="readonly"
                              photoUrls={returnData.return_photo_urls}
                            />
                          )}
                        {permissions?.canUploadPhotos && (
                          <div className="mt-3 space-y-3">
                            <DragDropZone
                              accept="image/*"
                              maxFiles={5}
                              label="Drop return photos here"
                              files={pendingPhotos}
                              onFilesChange={setPendingPhotos}
                            />
                            {pendingPhotos.length > 0 && (
                              <Button
                                loading={isUploading}
                                onClick={() => void handleUploadPhotos()}
                              >
                                Upload Photos
                              </Button>
                            )}
                          </div>
                        )}
                        {(!returnData.return_photo_urls ||
                          returnData.return_photo_urls.length === 0) &&
                          !permissions?.canUploadPhotos && (
                            <p className="text-sm text-muted-foreground">
                              No photos uploaded yet.
                            </p>
                          )}
                      </>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Employee Evidence */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-wider flex items-center gap-2">
                  <User className="size-4" />
                  Employee Evidence
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div>
                  <p className="text-xs font-semibold text-muted-foreground mb-2">
                    Employee Signature
                  </p>
                  {returnData.user_signature_url ? (
                    <img
                      src={returnData.user_signature_url}
                      alt="Employee signature"
                      className="h-24 border rounded-lg bg-white object-contain p-2"
                    />
                  ) : (
                    <p className="text-sm text-muted-foreground italic">
                      Pending employee signature.
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Completion */}
            {returnData.completed_at && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm uppercase tracking-wider">
                    Completion
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <dl className="grid grid-cols-2 gap-4">
                    <DetailItem
                      label="Completed At"
                      value={formatDate(returnData.completed_at) || '—'}
                    />
                    {returnData.completed_by && (
                      <DetailItem
                        label="Completed By"
                        value={returnData.completed_by}
                      />
                    )}
                    {returnData.resolved_status && (
                      <div>
                        <dt className="text-xs font-semibold text-muted-foreground mb-1">
                          Resolved Status
                        </dt>
                        <dd>
                          <ReturnStatusBadge
                            status={returnData.resolved_status as ReturnStatus}
                          />
                        </dd>
                      </div>
                    )}
                  </dl>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right sidebar */}
          <div className="space-y-4">
            {/* Status card */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-wider">
                  Status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-2">
                  <Badge
                    variant={
                      AssetStatusVariants[returnData.asset_status] ?? 'warning'
                    }
                  >
                    {AssetStatusLabels[returnData.asset_status] ??
                      returnData.asset_status}
                  </Badge>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Calendar className="size-4" />
                  {formatDate(returnData.initiated_at) || '—'}
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <User className="size-4" />
                  {returnData.initiated_by}
                </div>
              </CardContent>
            </Card>

            {/* Actions card */}
            {permissions &&
              (permissions.canRenotifyEmployee ||
                permissions.canSignAndComplete) && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm uppercase tracking-wider">
                      Actions
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-2">
                    {permissions.canRenotifyEmployee && (
                      <Button
                        variant="outline"
                        className="justify-start"
                        onClick={handleRenotify}
                        disabled={renotifyMutation.isPending}
                      >
                        <RefreshCw className="size-4" />
                        Re-notify Employee
                      </Button>
                    )}
                    {permissions.canSignAndComplete && (
                      <Button
                        className="justify-start"
                        onClick={() => setEmployeeSignatureOpen(true)}
                      >
                        <User className="size-4" />
                        Sign &amp; Complete Return
                      </Button>
                    )}
                  </CardContent>
                </Card>
              )}
          </div>
        </div>
      )}

      {/* Dialogs */}
      {returnData && (
        <Suspense fallback={null}>
          <EmployeeSignatureDialog
            open={employeeSignatureOpen}
            onOpenChange={setEmployeeSignatureOpen}
            assetId={asset_id}
            returnId={return_id}
            returnData={returnData}
            employeeName={returnData.initiated_by}
            onSuccess={() => {
              setEmployeeSignatureOpen(false)
              void navigate({ to: '/' })
            }}
          />
        </Suspense>
      )}
    </main>
  )
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function ReturnDetailSkeleton() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
      <div className="lg:col-span-2 space-y-6">
        {Array.from({ length: 3 }).map((_, i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-4 w-28" />
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-4">
                {Array.from({ length: 4 }).map((_, j) => (
                  <div key={j} className="space-y-1.5">
                    <Skeleton className="h-3 w-20" />
                    <Skeleton className="h-4 w-32" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <Skeleton className="h-4 w-16" />
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-5 w-24 rounded-full" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-28" />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

// ── Helper ────────────────────────────────────────────────────────────────────

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold text-muted-foreground mb-1">
        {label}
      </dt>
      <dd className="text-sm">{value}</dd>
    </div>
  )
}
