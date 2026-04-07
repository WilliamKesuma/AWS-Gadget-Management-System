import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '#/components/ui/dialog'
import { Button } from '#/components/ui/button'
import { Textarea } from '#/components/ui/textarea'
import { Field, FieldGroup, FieldLabel } from '#/components/ui/field'
import { useManagementReviewDisposal } from '#/hooks/use-disposals'
import { ApiError } from '#/lib/api-client'

type ApproveDisposalDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  assetId: string
  disposalId: string
}

export function ApproveDisposalDialog({
  open,
  onOpenChange,
  assetId,
  disposalId,
}: ApproveDisposalDialogProps) {
  const mutation = useManagementReviewDisposal(assetId, disposalId)
  const [remarks, setRemarks] = useState('')

  useEffect(() => {
    setRemarks('')
  }, [open])

  const handleConfirm = async () => {
    try {
      await mutation.mutateAsync({
        decision: 'APPROVE',
        remarks: remarks.trim() || undefined,
      })
      toast.success('Disposal request approved.')
      onOpenChange(false)
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          toast.error('Disposal is not in DISPOSAL_PENDING status')
        } else {
          toast.error(err.message)
        }
      } else {
        toast.error('An unexpected error occurred. Please try again.')
      }
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Approve Disposal Request</DialogTitle>
          <DialogDescription>
            Confirm approval of this disposal request. You may add optional
            remarks.
          </DialogDescription>
        </DialogHeader>
        <div className="overflow-y-auto -mx-1 px-1">
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="approve-remarks">
                Remarks (Optional)
              </FieldLabel>
              <Textarea
                id="approve-remarks"
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                placeholder="Add any remarks..."
                rows={3}
              />
            </Field>
          </FieldGroup>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => void handleConfirm()}
            loading={mutation.isPending}
          >
            Confirm Approval
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
