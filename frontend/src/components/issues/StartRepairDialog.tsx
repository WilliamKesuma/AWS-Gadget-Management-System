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
import { useResolveRepair } from '#/hooks/use-issues'
import { ApiError } from '#/lib/api-client'

type StartRepairDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  assetId: string
  issueId: string
}

export function StartRepairDialog({
  open,
  onOpenChange,
  assetId,
  issueId,
}: StartRepairDialogProps) {
  const mutation = useResolveRepair(assetId, issueId)

  const form = useForm({
    defaultValues: { repair_notes: '' },
    onSubmit: async ({ value }) => {
      try {
        await mutation.mutateAsync({
          repair_notes: value.repair_notes || undefined,
        })
        toast.success('Repair initiated. Status updated to Under Repair.')
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
          <DialogTitle>Start Repair</DialogTitle>
          <DialogDescription>
            Initiate a repair for this issue. Add optional notes below.
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
                name="repair_notes"
                children={(field) => {
                  const isInvalid =
                    field.state.meta.isTouched && !field.state.meta.isValid
                  return (
                    <Field data-invalid={isInvalid}>
                      <FieldLabel htmlFor={field.name}>
                        Repair Notes (optional)
                      </FieldLabel>
                      <Textarea
                        id={field.name}
                        name={field.name}
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(e) => field.handleChange(e.target.value)}
                        aria-invalid={isInvalid}
                        placeholder="Add any notes about the repair..."
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
            Start Repair
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
