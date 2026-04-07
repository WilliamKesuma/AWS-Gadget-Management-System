import { useEffect, useState } from 'react'
import { useForm } from '@tanstack/react-form'
import { z } from 'zod'
import { toast } from 'sonner'
import { format } from 'date-fns'
import { CalendarIcon, AlertTriangle } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '#/components/ui/dialog'
import { Button } from '#/components/ui/button'
import { Checkbox } from '#/components/ui/checkbox'
import { Calendar } from '#/components/ui/calendar'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '#/components/ui/popover'
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '#/components/ui/field'
import { useCompleteDisposal } from '#/hooks/use-disposals'
import { ApiError } from '#/lib/api-client'
import { cn, formatDate } from '#/lib/utils'

// ── Schema ────────────────────────────────────────────────────────────────────

const completeDisposalSchema = z.object({
  disposal_date: z.string().min(1, 'Disposal date is required.'),
  data_wipe_confirmed: z.literal(true, {
    message: 'Data wipe confirmation is required.',
  }),
})

// ── Types ─────────────────────────────────────────────────────────────────────

type CompleteDisposalDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  assetId: string
  disposalId: string
  disposal: {
    disposal_reason: string
    justification: string
  }
}

// ── Component ─────────────────────────────────────────────────────────────────

export function CompleteDisposalDialog({
  open,
  onOpenChange,
  assetId,
  disposalId,
  disposal,
}: CompleteDisposalDialogProps) {
  const mutation = useCompleteDisposal(assetId, disposalId)
  const [calendarOpen, setCalendarOpen] = useState(false)

  const form = useForm({
    defaultValues: {
      disposal_date: '',
      data_wipe_confirmed: false as boolean,
    },
    validators: {
      onSubmit: completeDisposalSchema,
    },
    onSubmit: async ({ value }) => {
      try {
        const response = await mutation.mutateAsync({
          disposal_date: value.disposal_date,
          data_wipe_confirmed: true,
        })
        toast.success('Disposal completed. Asset is now disposed.')

        if (response.finance_notification_status === 'COMPLETED') {
          toast.info('Finance team has been notified for asset write-off.')
        } else if (
          response.finance_notification_status === 'NO_FINANCE_USERS'
        ) {
          toast.warning(
            'No finance users found. Finance notification could not be sent.',
          )
        } else if (response.finance_notification_status === 'FAILED') {
          toast.warning(
            'Finance notification failed. Please notify the finance team manually.',
          )
        }

        onOpenChange(false)
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 409) {
            toast.error('Disposal has not been approved by management')
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
          <DialogTitle>Complete Disposal</DialogTitle>
        </DialogHeader>

        <div className="overflow-y-auto -mx-1 px-1">
          <form
            id="complete-disposal-form"
            onSubmit={(e) => {
              e.preventDefault()
              e.stopPropagation()
              void form.handleSubmit()
            }}
          >
            <FieldGroup>
              {/* Read-only context */}
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3">
                  Disposal Context
                </p>
                <div className="rounded-md border bg-muted/50 p-4 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">
                      Disposal Reason
                    </span>
                    <span className="font-medium text-right max-w-[60%]">
                      {disposal.disposal_reason}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Justification</span>
                    <span className="font-medium text-right max-w-[60%]">
                      {disposal.justification}
                    </span>
                  </div>
                </div>
              </div>

              {/* Disposal Date */}
              <form.Field
                name="disposal_date"
                children={(field) => {
                  const isInvalid =
                    field.state.meta.isTouched && !field.state.meta.isValid
                  const parsed = field.state.value
                    ? new Date(field.state.value)
                    : undefined
                  const isValidDate = parsed && !Number.isNaN(parsed.getTime())

                  return (
                    <Field data-invalid={isInvalid}>
                      <FieldLabel htmlFor={field.name}>
                        Disposal Date
                      </FieldLabel>
                      <Popover
                        open={calendarOpen}
                        onOpenChange={setCalendarOpen}
                      >
                        <PopoverTrigger asChild>
                          <Button
                            id={field.name}
                            variant="outline"
                            aria-invalid={isInvalid}
                            className={cn(
                              'w-full justify-start text-left font-normal',
                              !field.state.value && 'text-muted-foreground',
                            )}
                            onBlur={field.handleBlur}
                          >
                            <CalendarIcon className="size-4" />
                            {isValidDate ? formatDate(parsed) : 'Pick a date'}
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-auto p-0" align="start">
                          <Calendar
                            mode="single"
                            selected={isValidDate ? parsed : undefined}
                            onSelect={(date) => {
                              field.handleChange(
                                date ? format(date, 'yyyy-MM-dd') : '',
                              )
                              setCalendarOpen(false)
                            }}
                            autoFocus
                          />
                        </PopoverContent>
                      </Popover>
                      {isInvalid && (
                        <FieldError errors={field.state.meta.errors} />
                      )}
                    </Field>
                  )
                }}
              />

              {/* Data Wipe Confirmed */}
              <form.Field
                name="data_wipe_confirmed"
                children={(field) => {
                  const isInvalid =
                    field.state.meta.isTouched && !field.state.meta.isValid

                  return (
                    <Field data-invalid={isInvalid}>
                      <div className="flex items-center gap-2">
                        <Checkbox
                          id={field.name}
                          checked={field.state.value}
                          onCheckedChange={(checked) =>
                            field.handleChange(checked === true)
                          }
                          onBlur={field.handleBlur}
                          aria-invalid={isInvalid}
                        />
                        <FieldLabel htmlFor={field.name} className="mb-0">
                          Data Wipe Confirmed
                        </FieldLabel>
                      </div>
                      {isInvalid && (
                        <FieldError errors={field.state.meta.errors} />
                      )}
                    </Field>
                  )
                }}
              />

              {/* Warning when checkbox unchecked */}
              <form.Subscribe
                selector={(state) => state.values.data_wipe_confirmed}
                children={(dataWipeConfirmed) =>
                  !dataWipeConfirmed ? (
                    <div className="flex items-start gap-2 rounded-md border border-warning bg-warning-subtle p-3 text-sm text-warning">
                      <AlertTriangle className="mt-0.5 size-4 shrink-0" />
                      <span>
                        You must confirm that the device data has been wiped
                        before completing the disposal.
                      </span>
                    </div>
                  ) : null
                }
              />
            </FieldGroup>
          </form>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <form.Subscribe
            selector={(state) => ({
              dataWipeConfirmed: state.values.data_wipe_confirmed,
              isPending: mutation.isPending,
            })}
            children={({ dataWipeConfirmed, isPending }) => (
              <Button
                form="complete-disposal-form"
                type="submit"
                variant="destructive"
                disabled={!dataWipeConfirmed || isPending}
                loading={isPending}
              >
                Confirm Disposal
              </Button>
            )}
          />
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
