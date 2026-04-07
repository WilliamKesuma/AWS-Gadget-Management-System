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
import { useCompleteRepair } from '#/hooks/use-issues'
import { ApiError } from '#/lib/api-client'

type CompleteRepairDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  assetId: string
  issueId: string
}

export function CompleteRepairDialog({
  open,
  onOpenChange,
  assetId,
  issueId,
}: CompleteRepairDialogProps) {
  const mutation = useCompleteRepair(assetId, issueId)

  const form = useForm({
    defaultValues: { completion_notes: '' },
    onSubmit: async ({ value }) => {
      try {
        await mutation.mutateAsync({
          completion_notes: value.completion_notes || undefined,
        })
        toast.success('Repair completed. Asset restored to Assigned status.')
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
          <DialogTitle>Complete Repair</DialogTitle>
          <DialogDescription>
            Mark this repair as complete. The asset will be restored to Assigned
            status.
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
                name="completion_notes"
                children={(field) => {
                  const isInvalid =
                    field.state.meta.isTouched && !field.state.meta.isValid
                  return (
                    <Field data-invalid={isInvalid}>
                      <FieldLabel htmlFor={field.name}>
                        Completion Notes (optional)
                      </FieldLabel>
                      <Textarea
                        id={field.name}
                        name={field.name}
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(e) => field.handleChange(e.target.value)}
                        aria-invalid={isInvalid}
                        placeholder="Add any notes about the completed repair..."
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
            Complete Repair
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
