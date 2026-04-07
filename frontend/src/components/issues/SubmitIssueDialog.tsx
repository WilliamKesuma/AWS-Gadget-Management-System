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
import { useSubmitIssue } from '#/hooks/use-issues'
import { ApiError } from '#/lib/api-client'

const submitIssueSchema = z.object({
  issue_description: z
    .string()
    .min(1, 'Issue description is required.')
    .refine(
      (v) => v.trim().length > 0,
      'Issue description cannot be whitespace only.',
    ),
})

type SubmitIssueDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  assetId: string
  onSuccess?: (issueId: string) => void
}

export function SubmitIssueDialog({
  open,
  onOpenChange,
  assetId,
  onSuccess,
}: SubmitIssueDialogProps) {
  const submitMutation = useSubmitIssue(assetId)
  const [submitError, setSubmitError] = useState<string>()

  const form = useForm({
    defaultValues: {
      issue_description: '',
    },
    validators: {
      onSubmit: submitIssueSchema,
    },
    onSubmit: async ({ value }) => {
      setSubmitError(undefined)
      try {
        const response = await submitMutation.mutateAsync({
          issue_description: value.issue_description.trim(),
          category: 'SOFTWARE',
        })
        toast.success(
          'Issue reported successfully. IT Admin has been notified.',
        )
        onOpenChange(false)
        onSuccess?.(response.issue_id)
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
          <DialogTitle>Report Issue</DialogTitle>
          <DialogDescription>
            Describe the problem with your assigned gadget. Our IT team will
            review it shortly.
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
                name="issue_description"
                children={(field) => {
                  const isInvalid =
                    field.state.meta.isTouched && !field.state.meta.isValid
                  return (
                    <Field data-invalid={isInvalid}>
                      <FieldLabel htmlFor={field.name}>
                        Description of Issue
                      </FieldLabel>
                      <Textarea
                        id={field.name}
                        name={field.name}
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(e) => field.handleChange(e.target.value)}
                        aria-invalid={isInvalid}
                        placeholder="Describe what happened, any error codes, or physical damage..."
                        rows={5}
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
            loading={submitMutation.isPending}
          >
            Submit Report
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
