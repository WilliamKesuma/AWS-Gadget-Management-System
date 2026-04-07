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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '#/components/ui/select'
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '#/components/ui/field'
import { useManagementReviewSoftwareRequest } from '#/hooks/use-software-requests'
import { ApiError } from '#/lib/api-client'

// ─── Schema (module scope) ────────────────────────────────────────────────────

const managementReviewSchema = z
  .object({
    decision: z
      .enum(['', 'APPROVE', 'REJECT'])
      .refine((v) => v === 'APPROVE' || v === 'REJECT', {
        message: 'Please select a decision.',
      }),
    remarks: z.string(),
    rejection_reason: z.string(),
  })
  .refine(
    (data) =>
      data.decision !== 'REJECT' ||
      (data.rejection_reason && data.rejection_reason.trim().length > 0),
    {
      message: 'Rejection reason is required when rejecting.',
      path: ['rejection_reason'],
    },
  )

// ─── Success toast map ────────────────────────────────────────────────────────

const DECISION_TOASTS: Record<string, string> = {
  APPROVE: 'Software installation approved by Management.',
  REJECT: 'Software installation request rejected by Management.',
}

// ─── Props ────────────────────────────────────────────────────────────────────

type ManagementReviewDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  assetId: string
  softwareRequestId: string
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ManagementReviewDialog({
  open,
  onOpenChange,
  assetId,
  softwareRequestId,
}: ManagementReviewDialogProps) {
  const reviewMutation = useManagementReviewSoftwareRequest(
    assetId,
    softwareRequestId,
  )
  const [submitError, setSubmitError] = useState<string>()

  const form = useForm({
    defaultValues: {
      decision: '' as 'APPROVE' | 'REJECT' | '',
      remarks: '',
      rejection_reason: '',
    },
    validators: {
      onSubmit: managementReviewSchema,
    },
    onSubmit: async ({ value }) => {
      setSubmitError(undefined)
      try {
        await reviewMutation.mutateAsync({
          decision: value.decision as 'APPROVE' | 'REJECT',
          ...(value.remarks && value.remarks.trim().length > 0
            ? { remarks: value.remarks }
            : {}),
          ...(value.decision === 'REJECT' && value.rejection_reason
            ? { rejection_reason: value.rejection_reason }
            : {}),
        })
        toast.success(DECISION_TOASTS[value.decision])
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

  // Reset form and submitError when dialog opens/closes
  useEffect(() => {
    form.reset()
    setSubmitError(undefined)
  }, [open])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Review Escalated Request</DialogTitle>
          <DialogDescription>
            Make a final decision on this escalated software installation
            request.
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
              {/* Decision + conditional Rejection Reason via form.Subscribe */}
              <form.Subscribe
                selector={(state) => ({
                  currentDecision: state.values.decision,
                })}
                children={({ currentDecision }) => (
                  <>
                    {/* Decision */}
                    <form.Field
                      name="decision"
                      children={(field) => {
                        const isInvalid =
                          field.state.meta.isTouched &&
                          !field.state.meta.isValid
                        return (
                          <Field data-invalid={isInvalid}>
                            <FieldLabel htmlFor={field.name}>
                              Decision
                            </FieldLabel>
                            <Select
                              name={field.name}
                              value={field.state.value}
                              onValueChange={(v) =>
                                field.handleChange(v as 'APPROVE' | 'REJECT')
                              }
                            >
                              <SelectTrigger
                                id={field.name}
                                aria-invalid={isInvalid}
                                className="w-full"
                              >
                                <SelectValue placeholder="Select decision" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="APPROVE">Approve</SelectItem>
                                <SelectItem value="REJECT">Reject</SelectItem>
                              </SelectContent>
                            </Select>
                            {isInvalid && (
                              <FieldError errors={field.state.meta.errors} />
                            )}
                          </Field>
                        )
                      }}
                    />

                    {/* Remarks — always visible, optional */}
                    <form.Field
                      name="remarks"
                      children={(field) => {
                        const isInvalid =
                          field.state.meta.isTouched &&
                          !field.state.meta.isValid
                        return (
                          <Field data-invalid={isInvalid}>
                            <FieldLabel htmlFor={field.name}>
                              Remarks
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
                            />
                            {isInvalid && (
                              <FieldError errors={field.state.meta.errors} />
                            )}
                          </Field>
                        )
                      }}
                    />

                    {/* Rejection Reason — only when decision is REJECT */}
                    {currentDecision === 'REJECT' && (
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
                              />
                              {isInvalid && (
                                <FieldError errors={field.state.meta.errors} />
                              )}
                            </Field>
                          )
                        }}
                      />
                    )}
                  </>
                )}
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
            loading={reviewMutation.isPending}
          >
            Submit Review
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
