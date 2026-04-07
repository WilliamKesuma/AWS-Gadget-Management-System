import { useEffect } from 'react'
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
import { useCancelAssignment } from '#/hooks/use-assets'
import { ApiError } from '#/lib/api-client'

type CancelAssignmentDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  assetId: string
  onSuccess?: () => void
}

export function CancelAssignmentDialog({
  open,
  onOpenChange,
  assetId,
  onSuccess,
}: CancelAssignmentDialogProps) {
  const cancelAssignment = useCancelAssignment(assetId)

  // Reset mutation state when dialog opens/closes
  useEffect(() => {
    cancelAssignment.reset()
  }, [open])

  const handleConfirm = () => {
    cancelAssignment.mutate(undefined, {
      onSuccess: () => {
        toast.success('Assignment cancelled successfully.')
        onOpenChange(false)
        onSuccess?.()
      },
      onError: (err) => {
        if (err instanceof ApiError) {
          toast.error(err.message)
        } else {
          toast.error('An unexpected error occurred. Please try again.')
        }
      },
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Cancel Assignment</DialogTitle>
          <DialogDescription>
            Are you sure you want to cancel this assignment? The asset will
            return to IN_STOCK.
          </DialogDescription>
        </DialogHeader>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={cancelAssignment.isPending}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleConfirm}
            loading={cancelAssignment.isPending}
          >
            Confirm Cancel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
