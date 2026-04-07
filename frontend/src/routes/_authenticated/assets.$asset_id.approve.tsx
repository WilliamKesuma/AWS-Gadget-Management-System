import {
  createFileRoute,
  redirect,
  Link,
  useNavigate,
} from '@tanstack/react-router'
import { useState, useCallback } from 'react'
import {
  Package,
  ReceiptText,
  CreditCard,
  FileText,
  Download,
  RefreshCw,
  ImageIcon,
  Info,
  ShieldCheck,
  Cpu,
} from 'lucide-react'
import { hasRole } from '#/lib/permissions'
import type { UserRole } from '#/lib/models/types'
import {
  getBaseMeta,
  getPageMeta,
  getCanonicalLink,
  type SeoPageInput,
} from '../../lib/seo'
import { useAssetDetail, useApproveAsset } from '#/hooks/use-assets'
import { ApiError } from '#/lib/api-client'
import { formatDate, formatNumber } from '#/lib/utils'
import { AssetStatusLabels } from '#/lib/models/labels'
import { AssetStatusVariants } from '#/lib/models/badge-variants'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Separator } from '#/components/ui/separator'
import { Skeleton } from '#/components/ui/skeleton'
import { Textarea } from '#/components/ui/textarea'
import { Label } from '#/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '#/components/ui/dialog'
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselPrevious,
  CarouselNext,
} from '#/components/ui/carousel'

const APPROVE_ALLOWED: UserRole[] = ['management']

const ASSET_APPROVE_SEO = {
  title: 'Review Asset',
  description:
    'Review full asset details and approve or reject a pending asset submission as a management user.',
  path: '/assets/approve',
} satisfies SeoPageInput

export const Route = createFileRoute(
  '/_authenticated/assets/$asset_id/approve' as any,
)({
  beforeLoad: ({ context }) => {
    if (
      !hasRole(
        (context as { userRole?: UserRole | null }).userRole ?? null,
        APPROVE_ALLOWED,
      )
    ) {
      throw redirect({ to: '/unauthorized' })
    }
  },
  component: ApproveAssetDialog,
  head: () => ({
    meta: [
      ...getBaseMeta(),
      { name: 'robots', content: 'noindex, nofollow' },
      ...getPageMeta(ASSET_APPROVE_SEO),
    ],
    links: [getCanonicalLink(ASSET_APPROVE_SEO.path)],
  }),
})

// ── Detail field helper ───────────────────────────────────────────────────────

function DetailField({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {label}
      </p>
      <p className="text-sm">{children}</p>
    </div>
  )
}

// ── Section header ────────────────────────────────────────────────────────────

function SectionHeader({
  icon: Icon,
  title,
}: {
  icon: React.ElementType
  title: string
}) {
  return (
    <div className="flex items-center gap-2 pt-1">
      <Icon className="size-4 text-muted-foreground" strokeWidth={1.5} />
      <span className="text-sm font-semibold text-foreground">{title}</span>
    </div>
  )
}

// ── Presigned image with error handling ───────────────────────────────────────

function PresignedImage({
  src,
  alt,
  onError,
}: {
  src: string
  alt: string
  onError: () => void
}) {
  const [failed, setFailed] = useState(false)

  if (failed) {
    return (
      <div className="flex flex-col items-center justify-center h-64 bg-muted rounded-lg gap-2">
        <ImageIcon className="size-8 text-muted-foreground" />
        <p className="text-xs text-muted-foreground">Image failed to load</p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setFailed(false)
            onError()
          }}
        >
          <RefreshCw className="size-3 mr-1" />
          Refresh
        </Button>
      </div>
    )
  }

  return (
    <img
      src={src}
      alt={alt}
      className="w-full h-64 object-contain rounded-lg bg-muted"
      onError={() => setFailed(true)}
    />
  )
}

// ── Main component ────────────────────────────────────────────────────────────

function ApproveAssetDialog() {
  const { asset_id } = Route.useParams() as { asset_id: string }
  const navigate = useNavigate()
  const { data: asset, isLoading, error, refetch } = useAssetDetail(asset_id)
  const approveAsset = useApproveAsset(asset_id)

  const [action, setAction] = useState<'idle' | 'approve' | 'reject'>('idle')
  const [remarks, setRemarks] = useState('')
  const [rejectionReason, setRejectionReason] = useState('')

  const handleClose = useCallback(() => {
    void navigate({ to: '/assets', search: {} })
  }, [navigate])

  const handleRefreshUrls = useCallback(() => {
    void refetch()
  }, [refetch])

  return (
    <Dialog open onOpenChange={(open) => !open && handleClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Review Asset {asset_id}</DialogTitle>
          <DialogDescription>
            Review asset details and approve or reject this submission.
          </DialogDescription>
        </DialogHeader>

        {isLoading && <ApproveAssetSkeleton />}

        {error && (
          <div className="alert-danger">{(error as Error).message}</div>
        )}

        {asset && (
          <div className="overflow-y-auto -mx-1 px-1 space-y-5">
            {/* Status */}
            <div className="flex items-center gap-2">
              <Badge variant={AssetStatusVariants[asset.status] ?? 'info'}>
                {AssetStatusLabels[asset.status]}
              </Badge>
            </div>

            {/* Device info */}
            <SectionHeader icon={Package} title="Device Information" />
            <div className="grid grid-cols-2 gap-x-6 gap-y-3">
              <DetailField label="Brand">{asset.brand ?? '—'}</DetailField>
              <DetailField label="Model">{asset.model ?? '—'}</DetailField>
              <DetailField label="Serial Number">
                {asset.serial_number ?? '—'}
              </DetailField>
              <DetailField label="Category">
                {asset.category ?? '—'}
              </DetailField>
              <DetailField label="Condition">
                {asset.condition ?? '—'}
              </DetailField>
              <DetailField label="Created">
                {formatDate(asset.created_at) || '—'}
              </DetailField>
              {asset.product_description && (
                <div className="col-span-2">
                  <DetailField label="Product Description">
                    {asset.product_description}
                  </DetailField>
                </div>
              )}
            </div>

            {/* Technical Specs */}
            {(asset.processor ||
              asset.memory ||
              asset.storage ||
              asset.os_version) && (
                <>
                  <Separator />
                  <SectionHeader icon={Cpu} title="Technical Specifications" />
                  <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                    {asset.processor && (
                      <DetailField label="Processor">
                        {asset.processor}
                      </DetailField>
                    )}
                    {asset.memory && (
                      <DetailField label="Memory">{asset.memory}</DetailField>
                    )}
                    {asset.storage && (
                      <DetailField label="Storage">{asset.storage}</DetailField>
                    )}
                    {asset.os_version && (
                      <DetailField label="OS Version">
                        {asset.os_version}
                      </DetailField>
                    )}
                  </div>
                </>
              )}

            <Separator />

            {/* Purchase & Invoice */}
            <SectionHeader icon={ReceiptText} title="Purchase & Invoice" />
            <div className="grid grid-cols-2 gap-x-6 gap-y-3">
              <DetailField label="Invoice Number">
                {asset.invoice_number ?? '—'}
              </DetailField>
              <DetailField label="Vendor">{asset.vendor ?? '—'}</DetailField>
              <DetailField label="Purchase Date">
                {formatDate(asset.purchase_date) || '—'}
              </DetailField>
            </div>

            <Separator />

            {/* Cost & Payment */}
            <SectionHeader icon={CreditCard} title="Cost & Payment" />
            <div className="grid grid-cols-2 gap-x-6 gap-y-3">
              <DetailField label="Cost">
                {asset.cost != null ? formatNumber(asset.cost) : '—'}
              </DetailField>
              <DetailField label="Payment Method">
                {asset.payment_method ?? '—'}
              </DetailField>
            </div>

            {/* Remarks / Rejection */}
            {(asset.remarks || asset.rejection_reason) && (
              <>
                <Separator />
                <SectionHeader icon={Info} title="Additional Info" />
                <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                  {asset.remarks && (
                    <DetailField label="Remarks">{asset.remarks}</DetailField>
                  )}
                  {asset.rejection_reason && (
                    <DetailField label="Rejection Reason">
                      <span className="text-danger">
                        {asset.rejection_reason}
                      </span>
                    </DetailField>
                  )}
                </div>
              </>
            )}

            {/* Invoice document */}
            {asset.invoice_url && (
              <>
                <Separator />
                <SectionHeader icon={FileText} title="Invoice Document" />
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" asChild>
                    <a
                      href={asset.invoice_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Download className="size-3 mr-1" />
                      View / Download Invoice
                    </a>
                  </Button>
                </div>
              </>
            )}

            {/* Gadget photos */}
            {asset.gadget_photo_urls && asset.gadget_photo_urls.length > 0 && (
              <>
                <Separator />
                <div className="flex items-center justify-between">
                  <SectionHeader icon={ImageIcon} title="Gadget Photos" />
                  <Button variant="ghost" size="sm" onClick={handleRefreshUrls}>
                    <RefreshCw className="size-3 mr-1" />
                    Refresh
                  </Button>
                </div>
                {asset.gadget_photo_urls.length === 1 ? (
                  <PresignedImage
                    src={asset.gadget_photo_urls[0]}
                    alt={`${asset_id} photo`}
                    onError={handleRefreshUrls}
                  />
                ) : (
                  <div className="px-12">
                    <Carousel opts={{ loop: true }}>
                      <CarouselContent>
                        {asset.gadget_photo_urls.map((url, i) => (
                          <CarouselItem key={i}>
                            <PresignedImage
                              src={url}
                              alt={`${asset_id} photo ${i + 1}`}
                              onError={handleRefreshUrls}
                            />
                          </CarouselItem>
                        ))}
                      </CarouselContent>
                      <CarouselPrevious />
                      <CarouselNext />
                    </Carousel>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ── Approval footer ──────────────────────────────────── */}
        {asset && (
          <DialogFooter className="flex-col items-stretch gap-4 sm:flex-col">
            <SectionHeader icon={ShieldCheck} title="Review Decision" />

            {approveAsset.isSuccess && approveAsset.data ? (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  Status updated to{' '}
                  <span className="font-semibold">
                    {AssetStatusLabels[approveAsset.data.status]}
                  </span>
                </p>
                <Button asChild>
                  <Link to="/assets" search={{}}>
                    Back to List
                  </Link>
                </Button>
              </div>
            ) : (
              <>
                {approveAsset.isError && (
                  <p className="text-sm text-danger">
                    {(approveAsset.error as ApiError).message}
                  </p>
                )}

                {action === 'approve' && (
                  <div className="space-y-1.5">
                    <Label htmlFor="remarks">Remarks (optional)</Label>
                    <Textarea
                      id="remarks"
                      value={remarks}
                      onChange={(e) => setRemarks(e.target.value)}
                      placeholder="Add any remarks..."
                    />
                  </div>
                )}

                {action === 'reject' && (
                  <div className="space-y-1.5">
                    <Label htmlFor="rejection-reason">Rejection Reason</Label>
                    <Textarea
                      id="rejection-reason"
                      value={rejectionReason}
                      onChange={(e) => setRejectionReason(e.target.value)}
                      placeholder="Provide a reason for rejection..."
                    />
                  </div>
                )}

                <div className="flex gap-3">
                  {action === 'idle' && (
                    <>
                      <Button
                        variant="default"
                        onClick={() => setAction('approve')}
                      >
                        Approve
                      </Button>
                      <Button
                        variant="destructive"
                        onClick={() => setAction('reject')}
                      >
                        Reject
                      </Button>
                    </>
                  )}

                  {action === 'approve' && (
                    <>
                      <Button
                        variant="default"
                        loading={approveAsset.isPending}
                        onClick={() =>
                          approveAsset.mutate({
                            action: 'APPROVE',
                            remarks: remarks || undefined,
                          })
                        }
                      >
                        Confirm Approve
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => setAction('idle')}
                      >
                        Back
                      </Button>
                    </>
                  )}

                  {action === 'reject' && (
                    <>
                      <Button
                        variant="destructive"
                        disabled={
                          approveAsset.isPending ||
                          rejectionReason.trim() === ''
                        }
                        loading={approveAsset.isPending}
                        onClick={() =>
                          approveAsset.mutate({
                            action: 'REJECT',
                            rejection_reason: rejectionReason,
                          })
                        }
                      >
                        Confirm Reject
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => setAction('idle')}
                      >
                        Back
                      </Button>
                    </>
                  )}
                </div>
              </>
            )}
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function ApproveAssetSkeleton() {
  return (
    <div className="space-y-5">
      {/* Status badge */}
      <Skeleton className="h-5 w-24 rounded-full" />

      {/* Section: Device Information */}
      <div className="flex items-center gap-2">
        <Skeleton className="size-4 rounded" />
        <Skeleton className="h-4 w-36" />
      </div>
      <div className="grid grid-cols-2 gap-x-6 gap-y-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="space-y-1.5">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-4 w-32" />
          </div>
        ))}
      </div>

      <Skeleton className="h-px w-full" />

      {/* Section: Purchase & Invoice */}
      <div className="flex items-center gap-2">
        <Skeleton className="size-4 rounded" />
        <Skeleton className="h-4 w-36" />
      </div>
      <div className="grid grid-cols-2 gap-x-6 gap-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="space-y-1.5">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-4 w-28" />
          </div>
        ))}
      </div>

      <Skeleton className="h-px w-full" />

      {/* Section: Cost & Payment */}
      <div className="flex items-center gap-2">
        <Skeleton className="size-4 rounded" />
        <Skeleton className="h-4 w-32" />
      </div>
      <div className="grid grid-cols-2 gap-x-6 gap-y-3">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="space-y-1.5">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-4 w-28" />
          </div>
        ))}
      </div>

      <Skeleton className="h-px w-full" />

      {/* Gadget photos placeholder */}
      <div className="flex items-center gap-2">
        <Skeleton className="size-4 rounded" />
        <Skeleton className="h-4 w-28" />
      </div>
      <Skeleton className="h-64 w-full rounded-lg" />
    </div>
  )
}
