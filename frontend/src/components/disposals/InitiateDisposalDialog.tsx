import { useEffect } from 'react'
import { useForm } from '@tanstack/react-form'
import { z } from 'zod'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '#/components/ui/dialog'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { Textarea } from '#/components/ui/textarea'
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '#/components/ui/field'
import { useInitiateDisposal } from '#/hooks/use-disposals'
import { ApiError } from '#/lib/api-client'
import { formatNumber } from '#/lib/utils'

// ── Schema ────────────────────────────────────────────────────────────────────

const initiateDisposalSchema = z.object({
  disposal_reason: z
    .string()
    .min(1, 'Disposal reason is required.')
    .refine(
      (v) => v.trim().length > 0,
      'Disposal reason cannot be whitespace only.',
    ),
  justification: z
    .string()
    .min(1, 'Justification is required.')
    .refine(
      (v) => v.trim().length > 0,
      'Justification cannot be whitespace only.',
    ),
})

// ── Types ─────────────────────────────────────────────────────────────────────

type InitiateDisposalDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  assetId: string
  asset: {
    brand?: string
    model?: string
    serial_number?: string
    cost?: number
    category?: string
  }
}

// ── Component ─────────────────────────────────────────────────────────────────

export function InitiateDisposalDialog({
  open,
  onOpenChange,
  assetId,
  asset,
}: InitiateDisposalDialogProps) {
  const mutation = useInitiateDisposal(assetId)

  const form = useForm({
    defaultValues: {
      disposal_reason: '',
      justification: '',
    },
    validators: {
      onSubmit: initiateDisposalSchema,
    },
    onSubmit: async ({ value }) => {
      try {
        await mutation.mutateAsync({
          disposal_reason: value.disposal_reason.trim(),
          justification: value.justification.trim(),
        })
        toast.success(
          'Disposal request submitted. Awaiting management approval.',
        )
        onOpenChange(false)
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 404) {
            toast.error('Asset not found')
          } else if (err.status === 409) {
            toast.error('Asset is not in a valid status for disposal')
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
  }, [open])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Initiate Disposal</DialogTitle>
        </DialogHeader>

        <div className="overflow-y-auto -mx-1 px-1">
          <form
            id="initiate-disposal-form"
            onSubmit={(e) => {
              e.preventDefault()
              e.stopPropagation()
              void form.handleSubmit()
            }}
          >
            <FieldGroup>
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3">
                  Asset Details
                </p>
                <div className="rounded-md border bg-muted/50 p-4 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Brand</span>
                    <span className="font-medium">{asset.brand || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Model</span>
                    <span className="font-medium">{asset.model || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Serial Number</span>
                    <span className="font-medium">
                      {asset.serial_number || 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Cost</span>
                    <span className="font-medium">
                      {asset.cost != null ? formatNumber(asset.cost) : 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Category</span>
                    <span className="font-medium">
                      {asset.category || 'N/A'}
                    </span>
                  </div>
                </div>
              </div>

              <form.Field
                name="disposal_reason"
                children={(field) => {
                  const isInvalid =
                    field.state.meta.isTouched && !field.state.meta.isValid
                  return (
                    <Field data-invalid={isInvalid}>
                      <FieldLabel htmlFor={field.name}>
                        Disposal Reason
                      </FieldLabel>
                      <Input
                        id={field.name}
                        name={field.name}
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(e) => field.handleChange(e.target.value)}
                        aria-invalid={isInvalid}
                        placeholder="Enter the reason for disposal..."
                      />
                      {isInvalid && (
                        <FieldError errors={field.state.meta.errors} />
                      )}
                    </Field>
                  )
                }}
              />

              <form.Field
                name="justification"
                children={(field) => {
                  const isInvalid =
                    field.state.meta.isTouched && !field.state.meta.isValid
                  return (
                    <Field data-invalid={isInvalid}>
                      <FieldLabel htmlFor={field.name}>
                        Justification
                      </FieldLabel>
                      <Textarea
                        id={field.name}
                        name={field.name}
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(e) => field.handleChange(e.target.value)}
                        aria-invalid={isInvalid}
                        placeholder="Provide detailed justification for the disposal request..."
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
            form="initiate-disposal-form"
            type="submit"
            loading={mutation.isPending}
          >
            Submit Request
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
