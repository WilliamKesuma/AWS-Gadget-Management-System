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
import { Label } from '#/components/ui/label'
import { RadioGroup, RadioGroupItem } from '#/components/ui/radio-group'
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '#/components/ui/field'
import { useManagementReviewIssue } from '#/hooks/use-issues'
import { ApiError } from '#/lib/api-client'
import { ApproveRejectDecisionSchema } from '#/lib/models/types'

const reviewSchema = z.object({
  decision: ApproveRejectDecisionSchema,
  remarks: z.string(),
  rejection_reason: z.string(),
})

type ManagementReviewIssueDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  assetId: string
  issueId: string
}

export function ManagementReviewIssueDialog({
  open,
  onOpenChange,
  assetId,
  issueId,
}: ManagementReviewIssueDialogProps) {
  const mutation = useManagementReviewIssue(assetId, issueId)
  const [submitError, setSubmitError] = useState<string>()

  const form = useForm({
    defaultValues: {
      decision: 'REJECT',
      remarks: '',
      rejection_reason: '',
    },
    validators: {
      onSubmit: reviewSchema,
    },
    onSubmit: async ({ value }) => {
      setSubmitError(undefined)
      try {
        await mutation.mutateAsync({
          decision: value.decision as 'APPROVE' | 'REJECT',
          remarks: value.remarks || undefined,
          rejection_reason:
            value.decision === 'REJECT'
              ? value.rejection_reason?.trim()
              : undefined,
        })
        if (value.decision === 'APPROVE') {
          toast.success('Replacement approved.')
        } else {
          toast.success('Replacement request rejected.')
        }
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
          <DialogTitle>Review Replacement Request</DialogTitle>
          <DialogDescription>
            Approve or reject this replacement request.
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
                name="decision"
                children={(field) => {
                  const isInvalid =
                    field.state.meta.isTouched && !field.state.meta.isValid
                  return (
                    <Field data-invalid={isInvalid}>
                      <FieldLabel>Decision</FieldLabel>
                      <RadioGroup
                        value={field.state.value}
                        onValueChange={(v) =>
                          field.handleChange(v as 'APPROVE' | 'REJECT')
                        }
                      >
                        <div className="flex items-center space-x-2">
                          <RadioGroupItem
                            value="APPROVE"
                            id="decision-approve"
                          />
                          <Label htmlFor="decision-approve">Approve</Label>
                        </div>
                        <div className="flex items-center space-x-2">
                          <RadioGroupItem value="REJECT" id="decision-reject" />
                          <Label htmlFor="decision-reject">Reject</Label>
                        </div>
                      </RadioGroup>
                      {isInvalid && (
                        <FieldError errors={field.state.meta.errors} />
                      )}
                    </Field>
                  )
                }}
              />

              <form.Field
                name="remarks"
                children={(field) => {
                  const isInvalid =
                    field.state.meta.isTouched && !field.state.meta.isValid
                  return (
                    <Field data-invalid={isInvalid}>
                      <FieldLabel htmlFor={field.name}>
                        Remarks (optional)
                      </FieldLabel>
                      <Textarea
                        id={field.name}
                        name={field.name}
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(e) => field.handleChange(e.target.value)}
                        aria-invalid={isInvalid}
                        placeholder="Add any remarks..."
                        rows={3}
                      />
                      {isInvalid && (
                        <FieldError errors={field.state.meta.errors} />
                      )}
                    </Field>
                  )
                }}
              />

              <form.Subscribe
                selector={(state) => state.values.decision}
                children={(decision) =>
                  decision === 'REJECT' ? (
                    <form.Field
                      name="rejection_reason"
                      children={(field) => {
                        const isInvalid =
                          field.state.meta.isTouched &&
                          !field.state.meta.isValid
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
                              onChange={(e) =>
                                field.handleChange(e.target.value)
                              }
                              aria-invalid={isInvalid}
                              placeholder="Explain why this replacement is being rejected..."
                              rows={3}
                            />
                            {isInvalid && (
                              <FieldError errors={field.state.meta.errors} />
                            )}
                          </Field>
                        )
                      }}
                    />
                  ) : null
                }
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
            Submit Review
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
