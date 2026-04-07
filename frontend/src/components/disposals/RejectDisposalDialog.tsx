import { useEffect } from 'react'
import { useForm } from '@tanstack/react-form'
import { z } from 'zod'
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
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '#/components/ui/field'
import { useManagementReviewDisposal } from '#/hooks/use-disposals'
import { ApiError } from '#/lib/api-client'

type RejectDisposalDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  assetId: string
  disposalId: string
}

const rejectFormSchema = z.object({
  rejection_reason: z
    .string()
    .transform((v) => v.trim())
    .pipe(z.string().min(1, 'Rejection reason is required.')),
})

export function RejectDisposalDialog({
  open,
  onOpenChange,
  assetId,
  disposalId,
}: RejectDisposalDialogProps) {
  const mutation = useManagementReviewDisposal(assetId, disposalId)

  const form = useForm({
    defaultValues: { rejection_reason: '' },
    validators: {
      onSubmit: rejectFormSchema,
    },
    onSubmit: async ({ value }) => {
      try {
        await mutation.mutateAsync({
          decision: 'REJECT',
          rejection_reason: value.rejection_reason.trim(),
        })
        toast.success('Disposal request rejected.')
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
    },
  })

  useEffect(() => {
    if (!open) {
      form.reset()
    }
  }, [open, form])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reject Disposal Request</DialogTitle>
          <DialogDescription>
            Provide a reason for rejecting this disposal request.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            e.stopPropagation()
            form.handleSubmit()
          }}
        >
          <div className="overflow-y-auto -mx-1 px-1">
            <FieldGroup>
              <form.Field
                name="rejection_reason"
                children={(field) => {
                  const isInvalid =
                    field.state.meta.isTouched && !field.state.meta.isValid
                  return (
                    <Field data-invalid={isInvalid}>
                      <FieldLabel htmlFor={field.name}>
                        Rejection Reason
                      </FieldLabel>
                      <Textarea
                        id={field.name}
                        name={field.name}
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(e) => field.handleChange(e.target.value)}
                        aria-invalid={isInvalid}
                        placeholder="Provide a reason for rejection..."
                        rows={3}
                      />
                      {isInvalid && (
                        <FieldError errors={field.state.meta.errors} />
                      )}
                    </Field>
                  )
                }}
              />
            </FieldGroup>
          </div>
          <DialogFooter className="mt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="destructive"
              loading={mutation.isPending}
            >
              Confirm Rejection
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
