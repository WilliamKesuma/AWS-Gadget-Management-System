import { useEffect } from 'react'
import { useForm } from '@tanstack/react-form'
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
import { useSendWarranty } from '#/hooks/use-issues'
import { ApiError } from '#/lib/api-client'

type SendWarrantyDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  assetId: string
  issueId: string
}

export function SendWarrantyDialog({
  open,
  onOpenChange,
  assetId,
  issueId,
}: SendWarrantyDialogProps) {
  const mutation = useSendWarranty(assetId, issueId)

  const form = useForm({
    defaultValues: { warranty_notes: '' },
    onSubmit: async ({ value }) => {
      try {
        await mutation.mutateAsync({
          warranty_notes: value.warranty_notes || undefined,
        })
        toast.success('Asset sent to warranty.')
        onOpenChange(false)
      } catch (err) {
        if (err instanceof ApiError) {
          toast.error(err.message)
        } else {
          toast.error('An unexpected error occurred. Please try again.')
        }
      }
    },
  })

  useEffect(() => {
    form.reset()
  }, [open])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Send to Warranty</DialogTitle>
          <DialogDescription>
            Send this asset to warranty. Add optional notes below.
          </DialogDescription>
        </DialogHeader>
        <div className="overflow-y-auto -mx-1 px-1">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              e.stopPropagation()
              void form.handleSubmit()
            }}
          >
            <FieldGroup>
              <form.Field
                name="warranty_notes"
                children={(field) => {
                  const isInvalid =
                    field.state.meta.isTouched && !field.state.meta.isValid
                  return (
                    <Field data-invalid={isInvalid}>
                      <FieldLabel htmlFor={field.name}>
                        Warranty Notes (optional)
                      </FieldLabel>
                      <Textarea
                        id={field.name}
                        name={field.name}
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(e) => field.handleChange(e.target.value)}
                        aria-invalid={isInvalid}
                        placeholder="Add any warranty-related notes..."
                        rows={4}
                      />
                      {isInvalid && (
                        <FieldError errors={field.state.meta.errors} />
                      )}
                    </Field>
                  )
                }}
              />
            </FieldGroup>
          </form>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => void form.handleSubmit()}
            loading={mutation.isPending}
          >
            Send to Warranty
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
