import {
  createFileRoute,
  redirect,
  useNavigate,
  Outlet,
  useMatchRoute,
  Link,
} from '@tanstack/react-router'
import { lazy, Suspense, useState, useCallback, useMemo, useEffect } from 'react'
import { z } from 'zod'
import type {
  UserRole,
  ReturnTrigger,
  ReturnCondition,
  DisposalStatus,
} from '#/lib/models/types'
import {
  SoftwareStatusSchema,
  RiskLevelSchema,
  DataAccessImpactSchema,
  ReturnTriggerSchema,
  ReturnConditionSchema,
  DisposalStatusSchema,
} from '#/lib/models/types'
import {
  getBaseMeta,
  getPageMeta,
  getCanonicalLink,
  type SeoPageInput,
} from '../../lib/seo'
import {
  useAssetDetail,
  useHandoverForm,
  useSignedHandoverForm,
} from '#/hooks/use-assets'
import { useCurrentUserRole, useCurrentUserId } from '#/hooks/use-current-user'
import { getHandoverState, getVisibleActions } from '#/lib/asset-utils'
import { getAssetDetailPermissions } from '#/lib/permissions'
import { toast } from 'sonner'
import { Skeleton } from '#/components/ui/skeleton'
import { Button } from '#/components/ui/button'
import { Card } from '#/components/ui/card'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '#/components/ui/tabs'
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbSeparator,
  BreadcrumbPage,
} from '#/components/ui/breadcrumb'
import { AssetHeroCard } from '#/components/assets/detail/AssetHeroCard'
import { AssetInfoCards } from '#/components/assets/detail/AssetInfoCards'
import { TechnicalSpecsCard } from '#/components/assets/detail/TechnicalSpecsCard'
import { PurchaseInvoiceCard } from '#/components/assets/detail/PurchaseInvoiceCard'
import { GadgetPhotosCard } from '#/components/assets/detail/GadgetPhotosCard'
import { AdditionalInfoCard } from '#/components/assets/detail/AdditionalInfoCard'
import { QuickActionsCard } from '#/components/assets/detail/QuickActionsCard'
import { CurrentAssigneeCard } from '#/components/assets/detail/CurrentAssigneeCard'
import { useCursorPagination } from '#/hooks/use-cursor-pagination'
import { useIssues } from '#/hooks/use-issues'
import { IssueCard } from '#/components/issues/IssueCard'
import { hasRole } from '#/lib/permissions'

// Lazy-loaded tab components
const SoftwareRequestsTab = lazy(() =>
  import('#/components/software/SoftwareRequestsTab').then((m) => ({
    default: m.SoftwareRequestsTab,
  })),
)
const ReturnsTab = lazy(() =>
  import('#/components/returns/ReturnsTab').then((m) => ({
    default: m.ReturnsTab,
  })),
)
const DisposalsTab = lazy(() =>
  import('#/components/disposals/DisposalsTab').then((m) => ({
    default: m.DisposalsTab,
  })),
)
const LogsTab = lazy(() =>
  import('#/components/logs/LogsTab').then((m) => ({
    default: m.LogsTab,
  })),
)

// Lazy-loaded dialogs
const AssignAssetModal = lazy(() =>
  import('#/components/assets/AssignAssetModal').then((m) => ({
    default: m.AssignAssetModal,
  })),
)
const AcceptHandoverDialog = lazy(() =>
  import('#/components/assets/AcceptHandoverDialog').then((m) => ({
    default: m.AcceptHandoverDialog,
  })),
)
const CancelAssignmentDialog = lazy(() =>
  import('#/components/assets/CancelAssignmentDialog').then((m) => ({
    default: m.CancelAssignmentDialog,
  })),
)
const InitiateReturnDialog = lazy(() =>
  import('#/components/returns/InitiateReturnDialog').then((m) => ({
    default: m.InitiateReturnDialog,
  })),
)
const InitiateDisposalDialog = lazy(() =>
  import('#/components/disposals/InitiateDisposalDialog').then((m) => ({
    default: m.InitiateDisposalDialog,
  })),
)

const DETAIL_ALLOWED: UserRole[] = ['it-admin', 'management', 'employee']

const assetDetailSearchSchema = z.object({
  tab: z
    .enum(['software-requests', 'issues', 'returns', 'disposals', 'logs'])
    .optional(),
  sr_status: SoftwareStatusSchema.optional(),
  sr_risk_level: RiskLevelSchema.optional(),
  sr_software_name: z.string().optional(),
  sr_vendor: z.string().optional(),
  sr_license_validity_period: z.string().optional(),
  sr_data_access_impact: DataAccessImpactSchema.optional(),
  // Returns params
  ret_trigger: ReturnTriggerSchema.optional(),
  ret_condition: ReturnConditionSchema.optional(),
  initiate_return: z.boolean().optional(),
  // Disposals params
  disp_status: DisposalStatusSchema.optional(),
})

const ASSET_DETAIL_SEO = {
  title: 'Asset Detail',
  description:
    'View full asset details including metadata, invoice document, and gadget photos for review and management.',
  path: '/assets',
} satisfies SeoPageInput

export const Route = createFileRoute('/_authenticated/assets/$asset_id' as any)(
  {
    validateSearch: (raw: Record<string, unknown>) =>
      assetDetailSearchSchema.parse(raw),
    beforeLoad: ({ context }) => {
      if (
        !hasRole(
          (context as { userRole?: UserRole | null }).userRole ?? null,
          DETAIL_ALLOWED,
        )
      ) {
        throw redirect({ to: '/unauthorized' })
      }
    },
    component: AssetDetailPage,
    head: () => ({
      meta: [
        ...getBaseMeta(),
        { name: 'robots', content: 'noindex, nofollow' },
        ...getPageMeta(ASSET_DETAIL_SEO),
      ],
      links: [getCanonicalLink(ASSET_DETAIL_SEO.path)],
    }),
  },
)

function AssetDetailPage() {
  const { asset_id } = Route.useParams() as { asset_id: string }
  const navigate = useNavigate()
  const matchRoute = useMatchRoute()
  const { data: asset, isLoading, error } = useAssetDetail(asset_id)

  const role = useCurrentUserRole()
  const currentUserId = useCurrentUserId()
  const search = Route.useSearch()

  const handoverState = asset
    ? getHandoverState(asset.status, asset.assigned_date)
    : 'none'
  const isAssignedUser = role === 'employee'
  const visibleActions =
    role && asset
      ? getVisibleActions(role, asset.status, handoverState, isAssignedUser)
      : []

  const permissions = getAssetDetailPermissions({
    role,
    currentUserId,
    assigneeUserId: asset?.assignee?.user_id,
    assetStatus: asset?.status,
  })
  const {
    showSoftwareRequestsTab,
    showIssuesTab,
    showReportIssueButton,
    showRequestSoftwareButton,
    showInitiateReturnButton,
    showReturnsTab,
    showDisposalsTab,
    showInitiateDisposalButton,
    canInitiateDisposalAction,
    showManagementReviewButton,
    showLogsTab,
  } = permissions

  const isDisposed = asset?.status === 'DISPOSED'

  const showPurchaseInvoice = !hasRole(role, ['employee'])

  const [assignModalOpen, setAssignModalOpen] = useState(false)
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false)
  const [acceptDialogOpen, setAcceptDialogOpen] = useState(false)
  const [disposalDialogOpen, setDisposalDialogOpen] = useState(false)

  // Return flow state machine
  type ReturnFlowState =
    | { step: 'idle' }
    | { step: 'initiate' }
    | { step: 'done' }

  const [returnFlow, setReturnFlow] = useState<ReturnFlowState>({
    step: 'idle',
  })

  // Deep-link: if ?initiate_return=true, open the initiate dialog on mount
  useEffect(() => {
    if (search.initiate_return && returnFlow.step === 'idle') {
      setReturnFlow({ step: 'initiate' })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleCancelSuccess = useCallback(() => {
    void navigate({
      to: '/assets/$asset_id',
      params: { asset_id },
      search: {},
      replace: true,
    })
  }, [asset_id, navigate])

  const handoverFormMutation = useHandoverForm(asset_id)
  const signedHandoverFormMutation = useSignedHandoverForm(asset_id)

  const handleViewHandoverForm = useCallback(() => {
    handoverFormMutation.mutate(undefined, {
      onSuccess: (data) => {
        window.open(data.presigned_url, '_blank')
      },
      onError: (err) => {
        toast.error((err as Error).message || 'Failed to load handover form.')
      },
    })
  }, [handoverFormMutation])

  const handleViewSignedHandover = useCallback(() => {
    signedHandoverFormMutation.mutate(undefined, {
      onSuccess: (data) => {
        window.open(data.presigned_url, '_blank')
      },
      onError: (err) => {
        toast.error(
          (err as Error).message || 'Failed to load signed handover form.',
        )
      },
    })
  }, [signedHandoverFormMutation])

  const handleTabChange = useCallback(
    (tab: string) => {
      void navigate({
        to: '/assets/$asset_id' as any,
        params: { asset_id } as any,
        search: { tab } as any,
        replace: true,
      })
    },
    [asset_id, navigate],
  )

  // Build SoftwareRequestsTab search from prefixed params
  const softwareRequestsSearch = {
    status: search.sr_status,
    risk_level: search.sr_risk_level,
    software_name: search.sr_software_name,
    vendor: search.sr_vendor,
    license_validity_period: search.sr_license_validity_period,
    data_access_impact: search.sr_data_access_impact,
  }

  const handleSoftwareSearchChange = useCallback(
    (updates: Record<string, unknown>) => {
      const prefixed: Record<string, unknown> = {
        tab: 'software-requests',
      }
      const keyMap: Record<string, string> = {
        status: 'sr_status',
        risk_level: 'sr_risk_level',
        software_name: 'sr_software_name',
        vendor: 'sr_vendor',
        license_validity_period: 'sr_license_validity_period',
        data_access_impact: 'sr_data_access_impact',
      }
      // Carry over existing sr_ values
      for (const [, sr] of Object.entries(keyMap)) {
        const current = search[sr as keyof typeof search]
        if (current !== undefined) prefixed[sr] = current
      }
      // Apply updates
      for (const [key, value] of Object.entries(updates)) {
        const sr = keyMap[key] ?? key
        prefixed[sr] = value
      }
      void navigate({
        to: '/assets/$asset_id' as any,
        params: { asset_id } as any,
        search: prefixed as any,
        replace: true,
      })
    },
    [asset_id, search, navigate],
  )

  // Issues tab data
  const {
    currentCursor: issuesCursor,
    goToNextPage: issuesGoNext,
    goToPreviousPage: issuesGoPrev,
    canGoPrevious: issuesCanGoPrev,
  } = useCursorPagination(10)

  const {
    data: issuesData,
    isLoading: issuesLoading,
    error: issuesError,
  } = useIssues(asset_id, { history: true }, issuesCursor)
  const issueItems = useMemo(() => issuesData?.items ?? [], [issuesData])

  const handleReturnsSearchChange = useCallback(
    (updates: Record<string, unknown>) => {
      const keyMap: Record<string, string> = {
        return_trigger: 'ret_trigger',
        condition_assessment: 'ret_condition',
      }
      const prefixed: Record<string, unknown> = { tab: 'returns' }
      // Carry over existing ret_ values
      if (search.ret_trigger !== undefined)
        prefixed.ret_trigger = search.ret_trigger
      if (search.ret_condition !== undefined)
        prefixed.ret_condition = search.ret_condition
      // Apply updates
      for (const [key, value] of Object.entries(updates)) {
        const mapped = keyMap[key] ?? key
        prefixed[mapped] = value
      }
      void navigate({
        to: '/assets/$asset_id' as any,
        params: { asset_id } as any,
        search: prefixed as any,
        replace: true,
      })
    },
    [asset_id, search, navigate],
  )

  const handleDisposalsSearchChange = useCallback(
    (updates: Record<string, unknown>) => {
      const prefixed: Record<string, unknown> = { tab: 'disposals' }
      // Carry over existing disp_ values
      if (search.disp_status !== undefined)
        prefixed.disp_status = search.disp_status
      // Apply updates
      for (const [key, value] of Object.entries(updates)) {
        prefixed[key] = value
      }
      void navigate({
        to: '/assets/$asset_id' as any,
        params: { asset_id } as any,
        search: prefixed as any,
        replace: true,
      })
    },
    [asset_id, search, navigate],
  )

  // If the approve, software-requests, or issues child route is active, render only the child
  const isApproveActive = matchRoute({
    to: '/assets/$asset_id/approve' as any,
    params: { asset_id } as any,
    fuzzy: true,
  })
  const isSoftwareRequestsChildActive = matchRoute({
    to: '/assets/$asset_id/software-requests' as any,
    params: { asset_id } as any,
    fuzzy: true,
  })
  const isIssueDetailActive = matchRoute({
    to: '/assets/$asset_id/issues/$issue_id' as any,
    params: { asset_id } as any,
    fuzzy: true,
  })
  const isReturnDetailActive = matchRoute({
    to: '/assets/$asset_id/returns/$return_id' as any,
    params: { asset_id } as any,
    fuzzy: true,
  })
  const isDisposalDetailActive = matchRoute({
    to: '/assets/$asset_id/disposals/$disposal_id' as any,
    params: { asset_id } as any,
    fuzzy: true,
  })

  if (
    isApproveActive ||
    isSoftwareRequestsChildActive ||
    isIssueDetailActive ||
    isReturnDetailActive ||
    isDisposalDetailActive
  ) {
    return <Outlet />
  }

  return (
    <main className="page-base">
      {/* Breadcrumb */}
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link to="/assets">Assets</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{asset_id}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      {/* Disposed asset banner */}
      {isDisposed && (
        <div className="alert-warning mt-4">
          This asset has been disposed and is locked. No further actions are
          permitted.
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="mt-4 grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
          {/* Left column skeleton */}
          <div className="space-y-4">
            {/* Hero card */}
            <div className="rounded-xl border bg-card p-6 space-y-4">
              <div className="flex items-center gap-4">
                <Skeleton className="size-14 rounded-xl shrink-0" />
                <div className="space-y-2 flex-1">
                  <Skeleton className="h-5 w-48" />
                  <Skeleton className="h-4 w-32" />
                </div>
                <Skeleton className="h-6 w-20 rounded-full" />
              </div>
            </div>
            {/* Info cards */}
            <div className="grid grid-cols-2 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div
                  key={i}
                  className="rounded-xl border bg-card p-4 space-y-2"
                >
                  <Skeleton className="h-3 w-20" />
                  <Skeleton className="h-5 w-32" />
                </div>
              ))}
            </div>
            {/* Specs card */}
            <div className="rounded-xl border bg-card p-6 space-y-3">
              <Skeleton className="h-4 w-36" />
              <div className="grid grid-cols-2 gap-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="space-y-1.5">
                    <Skeleton className="h-3 w-20" />
                    <Skeleton className="h-4 w-28" />
                  </div>
                ))}
              </div>
            </div>
          </div>
          {/* Right sidebar skeleton */}
          <div className="space-y-4">
            <div className="rounded-xl border bg-card p-5 space-y-3">
              <Skeleton className="h-4 w-28" />
              <div className="flex items-center gap-3">
                <Skeleton className="size-10 rounded-full shrink-0" />
                <div className="space-y-1.5 flex-1">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-40" />
                </div>
              </div>
            </div>
            <div className="rounded-xl border bg-card p-5 space-y-3">
              <Skeleton className="h-4 w-24" />
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-9 w-full rounded-lg" />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="alert-danger mt-4">{(error as Error).message}</div>
      )}

      {/* Content */}
      {asset && (
        <div className="mt-4 grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
          {/* Left column */}
          <div className="space-y-4 min-w-0">
            <AssetHeroCard asset={asset} />
            <AssetInfoCards asset={asset} />
            <TechnicalSpecsCard asset={asset} />

            {/* Overview cards (flat, outside tabs) */}
            {showPurchaseInvoice && <PurchaseInvoiceCard asset={asset} />}
            <AdditionalInfoCard asset={asset} />
            {asset.gadget_photo_urls && asset.gadget_photo_urls.length > 0 && (
              <GadgetPhotosCard
                assetId={asset_id}
                photoUrls={asset.gadget_photo_urls}
              />
            )}

            {/* Tabs — only rendered when there are extra sections and asset is not disposed */}
            {(showSoftwareRequestsTab ||
              showIssuesTab ||
              showReturnsTab ||
              showDisposalsTab ||
              showLogsTab) && (
                <Tabs
                  value={
                    search.tab ??
                    (showDisposalsTab && isDisposed
                      ? 'disposals'
                      : showSoftwareRequestsTab
                        ? 'software-requests'
                        : showIssuesTab
                          ? 'issues'
                          : showReturnsTab
                            ? 'returns'
                            : showDisposalsTab
                              ? 'disposals'
                              : 'logs')
                  }
                  onValueChange={handleTabChange}
                >
                  <TabsList variant="line">
                    {showSoftwareRequestsTab && !isDisposed && (
                      <TabsTrigger value="software-requests">
                        Software Requests
                      </TabsTrigger>
                    )}
                    {showIssuesTab && !isDisposed && (
                      <TabsTrigger value="issues">Issues</TabsTrigger>
                    )}
                    {showReturnsTab && !isDisposed && (
                      <TabsTrigger value="returns">Returns</TabsTrigger>
                    )}
                    {showDisposalsTab && (
                      <TabsTrigger value="disposals">Disposals</TabsTrigger>
                    )}
                    {showLogsTab && (
                      <TabsTrigger value="logs">Logs</TabsTrigger>
                    )}
                  </TabsList>

                  {showSoftwareRequestsTab && !isDisposed && (
                    <TabsContent value="software-requests">
                      <div className="pt-4">
                        <Suspense fallback={<Skeleton className="h-64 w-full rounded-xl" />}>
                          <SoftwareRequestsTab
                            assetId={asset_id}
                            search={softwareRequestsSearch}
                            onSearchChange={handleSoftwareSearchChange}
                          />
                        </Suspense>
                      </div>
                    </TabsContent>
                  )}

                  {showIssuesTab && !isDisposed && (
                    <TabsContent value="issues">
                      <div className="pt-4">
                        {issuesLoading && (
                          <div className="space-y-3">
                            {Array.from({ length: 3 }).map((_, i) => (
                              <div
                                key={i}
                                className="rounded-xl border bg-card p-4 space-y-2"
                              >
                                <div className="flex items-center justify-between">
                                  <Skeleton className="h-4 w-40" />
                                  <Skeleton className="h-5 w-20 rounded-full" />
                                </div>
                                <Skeleton className="h-3 w-64" />
                                <Skeleton className="h-3 w-24" />
                              </div>
                            ))}
                          </div>
                        )}
                        {issuesError && (
                          <div className="alert-danger">
                            {(issuesError as Error).message}
                          </div>
                        )}
                        {!issuesLoading &&
                          !issuesError &&
                          issueItems.length === 0 && (
                            <p className="text-sm text-muted-foreground text-center py-12">
                              No issues reported for this asset.
                            </p>
                          )}
                        {!issuesLoading &&
                          !issuesError &&
                          issueItems.length > 0 && (
                            <Card className="gap-0 py-0">
                              {issueItems.map((issue) => (
                                <IssueCard
                                  key={`${issue.asset_id}-${issue.issue_id}`}
                                  issue={issue}
                                />
                              ))}
                            </Card>
                          )}
                        {(issuesData?.has_next_page || issuesCanGoPrev) && (
                          <div className="flex justify-center mt-4">
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={!issuesCanGoPrev}
                              onClick={issuesGoPrev}
                            >
                              Previous
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="ml-2"
                              disabled={!issuesData?.has_next_page}
                              onClick={() =>
                                issuesData?.next_cursor &&
                                issuesGoNext(issuesData.next_cursor)
                              }
                            >
                              Next
                            </Button>
                          </div>
                        )}
                      </div>
                    </TabsContent>
                  )}

                  {showReturnsTab && !isDisposed && (
                    <TabsContent value="returns">
                      <div className="pt-4">
                        <Suspense fallback={<Skeleton className="h-64 w-full rounded-xl" />}>
                          <ReturnsTab
                            assetId={asset_id}
                            search={{
                              ret_trigger: search.ret_trigger as
                                | ReturnTrigger
                                | undefined,
                              ret_condition: search.ret_condition as
                                | ReturnCondition
                                | undefined,
                            }}
                            onSearchChange={handleReturnsSearchChange}
                          />
                        </Suspense>
                      </div>
                    </TabsContent>
                  )}

                  {showDisposalsTab && (
                    <TabsContent value="disposals">
                      <div className="pt-4">
                        <Suspense fallback={<Skeleton className="h-64 w-full rounded-xl" />}>
                          <DisposalsTab
                            assetId={asset_id}
                            search={{
                              disp_status: search.disp_status as
                                | DisposalStatus
                                | undefined,
                            }}
                            onSearchChange={handleDisposalsSearchChange}
                          />
                        </Suspense>
                      </div>
                    </TabsContent>
                  )}

                  {showLogsTab && (
                    <TabsContent value="logs">
                      <div className="pt-4">
                        <Suspense fallback={<Skeleton className="h-64 w-full rounded-xl" />}>
                          <LogsTab assetId={asset_id} />
                        </Suspense>
                      </div>
                    </TabsContent>
                  )}
                </Tabs>
              )}
          </div>

          {/* Right sidebar */}
          <div className="space-y-4">
            {asset.assignee && (
              <CurrentAssigneeCard assignee={asset.assignee} />
            )}
            {!isDisposed && (
              <QuickActionsCard
                assetId={asset_id}
                visibleActions={visibleActions}
                onAssign={() => setAssignModalOpen(true)}
                onCancelAssignment={() => setCancelDialogOpen(true)}
                onAcceptAsset={() => setAcceptDialogOpen(true)}
                onViewHandoverForm={handleViewHandoverForm}
                onViewSignedHandover={handleViewSignedHandover}
                handoverFormPending={handoverFormMutation.isPending}
                signedHandoverPending={signedHandoverFormMutation.isPending}
                showReportIssue={showReportIssueButton}
                showRequestSoftware={showRequestSoftwareButton}
                showInitiateReturn={showInitiateReturnButton}
                onInitiateReturn={() => setReturnFlow({ step: 'initiate' })}
                showInitiateDisposal={showInitiateDisposalButton}
                canInitiateDisposal={canInitiateDisposalAction}
                onInitiateDisposal={() => setDisposalDialogOpen(true)}
                showManagementReview={showManagementReviewButton}
              />
            )}
          </div>
        </div>
      )}

      {/* Modals */}
      <Suspense fallback={null}>
        <AssignAssetModal
          open={assignModalOpen}
          onOpenChange={setAssignModalOpen}
          assetId={asset_id}
        />
        <CancelAssignmentDialog
          open={cancelDialogOpen}
          onOpenChange={setCancelDialogOpen}
          assetId={asset_id}
          onSuccess={handleCancelSuccess}
        />
        {asset && (
          <AcceptHandoverDialog
            open={acceptDialogOpen}
            onOpenChange={setAcceptDialogOpen}
            assetId={asset_id}
            asset={{
              brand: asset.brand,
              model: asset.model,
              serial_number: asset.serial_number,
              status: asset.status,
            }}
          />
        )}

        {/* Return flow dialogs */}
        {asset && returnFlow.step === 'initiate' && (
          <InitiateReturnDialog
            open
            onOpenChange={(open) => {
              if (!open) setReturnFlow({ step: 'idle' })
            }}
            assetId={asset_id}
            asset={{ model: asset.model, serial_number: asset.serial_number }}
            onSuccess={() => setReturnFlow({ step: 'done' })}
          />
        )}

        {/* Disposal dialog */}
        {asset && (
          <InitiateDisposalDialog
            open={disposalDialogOpen}
            onOpenChange={setDisposalDialogOpen}
            assetId={asset_id}
            asset={{
              brand: asset.brand,
              model: asset.model,
              serial_number: asset.serial_number,
              cost: asset.cost,
              category: asset.category,
            }}
          />
        )}
      </Suspense>

      <Outlet />
    </main>
  )
}
