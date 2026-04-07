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
import { useReviewSoftwareRequest } from '#/hooks/use-software-requests'
import { ApiError } from '#/lib/api-client'
import { RiskLevelLabels } from '#/lib/models/labels'
import {
  DataAccessImpactSchema,
  ReviewDecisionSchema,
  type ReviewDecision,
  type ReviewSoftwareRequestRequest,
  type RiskLevel,
} from '#/lib/models/types'

// ─── Schema (module scope) ────────────────────────────────────────────────────

const reviewSchema = z.object({
  risk_level: DataAccessImpactSchema,
  decision: ReviewDecisionSchema,
  rejection_reason: z.string(),
})

// ─── Decision constraint helper ───────────────────────────────────────────────

function getEnabledDecisions(riskLevel: string): Set<string> {
  if (riskLevel === 'LOW') return new Set(['APPROVE', 'REJECT'])
  if (riskLevel === 'MEDIUM' || riskLevel === 'HIGH')
    return new Set(['ESCALATE', 'REJECT'])
  return new Set()
}

// ─── Success toast map ────────────────────────────────────────────────────────

const DECISION_TOASTS: Record<string, string> = {
  APPROVE: 'Software installation approved.',
  ESCALATE: 'Request escalated to Management for review.',
  REJECT: 'Software installation request rejected.',
}

// ─── Props ────────────────────────────────────────────────────────────────────

type ITAdminReviewDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  assetId: string
  softwareRequestId: string
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ITAdminReviewDialog({
  open,
  onOpenChange,
  assetId,
  softwareRequestId,
}: ITAdminReviewDialogProps) {
  const reviewMutation = useReviewSoftwareRequest(assetId, softwareRequestId)
  const [submitError, setSubmitError] = useState<string>()

  const form = useForm({
    defaultValues: {
      risk_level: 'LOW',
      decision: 'REJECT',
      rejection_reason: '',
    },
    validators: {
      onSubmit: reviewSchema,
    },
    onSubmit: async ({ value }: { value: ReviewSoftwareRequestRequest }) => {
      setSubmitError(undefined)
      try {
        await reviewMutation.mutateAsync({
          risk_level: value.risk_level,
          decision: value.decision,
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
          <DialogTitle>Review Software Request</DialogTitle>
          <DialogDescription>
            Assess the risk level and make a decision on this software
            installation request.
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
              {/* Risk Level */}
              <form.Field
                name="risk_level"
                children={(field) => {
                  const isInvalid =
                    field.state.meta.isTouched && !field.state.meta.isValid
                  return (
                    <Field data-invalid={isInvalid}>
                      <FieldLabel htmlFor={field.name}>Risk Level</FieldLabel>
                      <Select
                        name={field.name}
                        value={field.state.value}
                        onValueChange={(val: RiskLevel) => {
                          field.handleChange(val)
                          const enabled = getEnabledDecisions(val!)
                          const currentDecision = form.getFieldValue('decision')
                          if (
                            currentDecision &&
                            !enabled.has(currentDecision)
                          ) {
                            form.setFieldValue('decision', 'REJECT')
                          }
                        }}
                      >
                        <SelectTrigger
                          id={field.name}
                          aria-invalid={isInvalid}
                          className="w-full"
                        >
                          <SelectValue placeholder="Select risk level" />
                        </SelectTrigger>
                        <SelectContent>
                          {Object.entries(RiskLevelLabels).map(
                            ([value, label]) => (
                              <SelectItem key={value} value={value}>
                                {label}
                              </SelectItem>
                            ),
                          )}
                        </SelectContent>
                      </Select>
                      {isInvalid && (
                        <FieldError errors={field.state.meta.errors} />
                      )}
                    </Field>
                  )
                }}
              />

              {/* Decision — use form.Subscribe to get current risk_level and decision */}
              <form.Subscribe
                selector={(state) => ({
                  riskLevel: state.values.risk_level,
                  currentDecision: state.values.decision,
                })}
                children={({ riskLevel, currentDecision }) => {
                  const enabledDecisions = getEnabledDecisions(riskLevel)
                  return (
                    <>
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
                                onValueChange={(v: ReviewDecision) =>
                                  field.handleChange(v)
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
                                  <SelectItem
                                    value="APPROVE"
                                    disabled={!enabledDecisions.has('APPROVE')}
                                  >
                                    Approve
                                  </SelectItem>
                                  <SelectItem
                                    value="ESCALATE"
                                    disabled={!enabledDecisions.has('ESCALATE')}
                                  >
                                    Escalate to Management
                                  </SelectItem>
                                  <SelectItem
                                    value="REJECT"
                                    disabled={!enabledDecisions.has('REJECT')}
                                  >
                                    Reject
                                  </SelectItem>
                                </SelectContent>
                              </Select>
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
                                  <FieldError
                                    errors={field.state.meta.errors}
                                  />
                                )}
                              </Field>
                            )
                          }}
                        />
                      )}
                    </>
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
            loading={reviewMutation.isPending}
          >
            Submit Review
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
