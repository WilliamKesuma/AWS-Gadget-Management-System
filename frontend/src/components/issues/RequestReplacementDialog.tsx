import { useState, useEffect } from 'react'
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
import { useRequestReplacement } from '#/hooks/use-issues'
import { ApiError } from '#/lib/api-client'

const replacementSchema = z.object({
  replacement_justification: z
    .string()
    .min(1, 'Replacement justification is required.')
    .refine(
      (v) => v.trim().length > 0,
      'Justification cannot be whitespace only.',
    ),
})

type RequestReplacementDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  assetId: string
  issueId: string
}

export function RequestReplacementDialog({
  open,
  onOpenChange,
  assetId,
  issueId,
}: RequestReplacementDialogProps) {
  const mutation = useRequestReplacement(assetId, issueId)
  const [submitError, setSubmitError] = useState<string>()

  const form = useForm({
    defaultValues: { replacement_justification: '' },
    validators: {
      onSubmit: replacementSchema,
    },
    onSubmit: async ({ value }) => {
      setSubmitError(undefined)
      try {
        await mutation.mutateAsync({
          replacement_justification: value.replacement_justification.trim(),
        })
        toast.success('Replacement request submitted. Management will review.')
        onOpenChange(false)
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 400) {
            setSubmitError(err.message)
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
    form.reset()
    setSubmitError(undefined)
  }, [open])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Request Replacement</DialogTitle>
          <DialogDescription>
            Submit a replacement request for this asset. Management will review
            your justification.
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
                name="replacement_justification"
                children={(field) => {
                  const isInvalid =
                    field.state.meta.isTouched && !field.state.meta.isValid
                  return (
                    <Field data-invalid={isInvalid}>
                      <FieldLabel htmlFor={field.name}>
                        Replacement Justification
                      </FieldLabel>
                      <Textarea
                        id={field.name}
                        name={field.name}
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(e) => field.handleChange(e.target.value)}
                        aria-invalid={isInvalid}
                        placeholder="Explain why this asset needs to be replaced..."
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
            {submitError && (
              <div className="alert-danger mt-4">{submitError}</div>
            )}
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
            Request Replacement
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
