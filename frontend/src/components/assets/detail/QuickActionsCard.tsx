import { Link } from '@tanstack/react-router'
import { Card, CardHeader, CardTitle, CardContent } from '#/components/ui/card'
import { Button } from '#/components/ui/button'
import { Separator } from '#/components/ui/separator'
import type { AssetAction } from '#/lib/asset-utils'

type QuickActionsCardProps = {
  assetId: string
  visibleActions: AssetAction[]
  onAssign: () => void
  onCancelAssignment: () => void
  onAcceptAsset: () => void
  onViewHandoverForm: () => void
  onViewSignedHandover: () => void
  handoverFormPending: boolean
  signedHandoverPending: boolean
  showReportIssue?: boolean
  showRequestSoftware?: boolean
  showInitiateReturn?: boolean
  onInitiateReturn?: () => void
  showInitiateDisposal?: boolean
  canInitiateDisposal?: boolean
  onInitiateDisposal?: () => void
  showManagementReview?: boolean
}

export function QuickActionsCard({
  assetId,
  visibleActions,
  onAssign,
  onCancelAssignment,
  onAcceptAsset,
  onViewHandoverForm,
  onViewSignedHandover,
  handoverFormPending,
  signedHandoverPending,
  showReportIssue = false,
  showRequestSoftware = false,
  showInitiateReturn = false,
  onInitiateReturn,
  showInitiateDisposal = false,
  canInitiateDisposal = false,
  onInitiateDisposal,
  showManagementReview = false,
}: QuickActionsCardProps) {
  // Group flags
  const hasHandoverActions = visibleActions.length > 0
  const hasLifecycleActions = showInitiateReturn || showInitiateDisposal
  const hasEmployeeActions = showReportIssue || showRequestSoftware

  const hasAnyAction =
    hasHandoverActions ||
    hasLifecycleActions ||
    hasEmployeeActions ||
    showManagementReview

  if (!hasAnyAction) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Quick Actions</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {/* ── Management Review ── */}
        {showManagementReview && (
          <Button variant="default" className="justify-start" asChild>
            <Link to="/assets/$asset_id/approve" params={{ asset_id: assetId }}>
              Review Asset
            </Link>
          </Button>
        )}

        {/* ── Handover Actions ── */}
        {visibleActions.includes('assign') && (
          <Button
            variant="outline"
            className="justify-start"
            onClick={onAssign}
          >
            Assign to Employee
          </Button>
        )}
        {visibleActions.includes('view-handover-form') && (
          <Button
            variant="outline"
            className="justify-start"
            onClick={onViewHandoverForm}
            loading={handoverFormPending}
          >
            View Handover Form
          </Button>
        )}
        {visibleActions.includes('view-signed-handover') && (
          <Button
            variant="outline"
            className="justify-start"
            onClick={onViewSignedHandover}
            loading={signedHandoverPending}
          >
            View Signed Handover
          </Button>
        )}
        {visibleActions.includes('accept-asset') && (
          <Button
            variant="outline"
            className="justify-start"
            onClick={onAcceptAsset}
          >
            Accept Asset
          </Button>
        )}
        {visibleActions.includes('cancel-assignment') && (
          <Button
            variant="outline"
            className="justify-start text-danger hover:text-danger"
            onClick={onCancelAssignment}
          >
            Cancel Assignment
          </Button>
        )}

        {/* ── Lifecycle Actions ── */}
        {hasHandoverActions && hasLifecycleActions && <Separator />}
        {showInitiateReturn && (
          <Button
            variant="outline"
            className="justify-start"
            onClick={onInitiateReturn}
          >
            Initiate Return
          </Button>
        )}
        {showInitiateDisposal && (
          <Button
            variant="outline"
            className="justify-start"
            onClick={onInitiateDisposal}
            disabled={!canInitiateDisposal}
          >
            Initiate Disposal
          </Button>
        )}

        {/* ── Employee Actions ── */}
        {(hasHandoverActions || hasLifecycleActions) && hasEmployeeActions && (
          <Separator />
        )}
        {showRequestSoftware && (
          <Button variant="outline" className="justify-start" asChild>
            <Link to="/requests/new-software">
              Request Software Installation
            </Link>
          </Button>
        )}
        {showReportIssue && (
          <Button
            className="justify-start bg-warning text-warning-foreground hover:bg-warning/80"
            asChild
          >
            <Link to="/requests/new-issue">Report Issue</Link>
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
