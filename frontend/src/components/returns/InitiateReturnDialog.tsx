import { useState, useRef, useEffect } from 'react'
import { useForm } from '@tanstack/react-form'
import { z } from 'zod'
import { toast } from 'sonner'
import SignatureCanvas from 'react-signature-canvas'
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
import { Field, FieldError, FieldLabel } from '#/components/ui/field'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '#/components/ui/select'
import { ReturnTriggerSelector } from './ReturnTriggerSelector'
import { AssetDetailsCard } from './AssetDetailsCard'
import { HandoverTimestampPill } from './HandoverTimestampPill'
import { EvidencePhotoGrid } from './EvidencePhotoGrid'
import { SignatureCard } from './SignatureCard'
import {
  useInitiateReturn,
  useGenerateReturnUploadUrls,
  useSubmitAdminEvidence,
} from '#/hooks/use-returns'
import { ApiError } from '#/lib/api-client'
import { ResetStatusLabels } from '#/lib/models/labels'
import {
  ReturnTriggerSchema,
  ReturnConditionSchema,
  ResetStatusSchema,
} from '#/lib/models/types'
import type {
  ReturnTrigger,
  ReturnCondition,
  ResetStatus,
} from '#/lib/models/types'

// ── Schema ────────────────────────────────────────────────────────────────────

const initiateReturnSchema = z.object({
  return_trigger: ReturnTriggerSchema,
  condition_assessment: ReturnConditionSchema,
  reset_status: ResetStatusSchema,
  remarks: z
    .string()
    .min(1, 'Remarks are required.')
    .refine((v) => v.trim().length > 0, 'Remarks cannot be whitespace only.'),
})

type UploadStep = 'form' | 'initiating' | 'uploading' | 'submitting' | 'done'

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  assetId: string
  asset: { model?: string; serial_number?: string }
  onSuccess: () => void
}

export function InitiateReturnDialog({
  open,
  onOpenChange,
  assetId,
  asset,
  onSuccess,
}: Props) {
  const [uploadStep, setUploadStep] = useState<UploadStep>('form')
  const [photos, setPhotos] = useState<File[]>([])
  const [submitError, setSubmitError] = useState<string>()
  const [photoError, setPhotoError] = useState<string>()
  const [signatureError, setSignatureError] = useState<string>()
  const [timestamp] = useState(() => new Date().toISOString())
  const sigRef = useRef<SignatureCanvas | null>(null)

  const isPending = uploadStep !== 'form'

  const initiateMutation = useInitiateReturn(assetId)
  const generateUrlsMutation = useGenerateReturnUploadUrls(assetId)
  const submitEvidenceMutation = useSubmitAdminEvidence(assetId)

  const form = useForm({
    defaultValues: {
      return_trigger: '' as ReturnTrigger | '',
      condition_assessment: '' as ReturnCondition | '',
      reset_status: '' as ResetStatus | '',
      remarks: '',
    },
    validators: {
      onSubmit: initiateReturnSchema,
    },
    onSubmit: async ({ value }) => {
      setSubmitError(undefined)
      setPhotoError(undefined)
      setSignatureError(undefined)

      let hasError = false

      if (photos.length === 0) {
        setPhotoError('At least one photo is required.')
        hasError = true
      }

      const canvas = sigRef.current
      if (!canvas || canvas.isEmpty()) {
        setSignatureError('Admin signature is required.')
        hasError = true
      }

      if (hasError) return

      try {
        // Export signature blob
        const sigBlob = await new Promise<Blob>((resolve, reject) => {
          sigRef.current!.getCanvas().toBlob((blob) => {
            if (blob) resolve(blob)
            else reject(new Error('Failed to export signature.'))
          }, 'image/png')
        })

        // Step 1 — initiate return
        setUploadStep('initiating')
        const { return_id } = await initiateMutation.mutateAsync({
          return_trigger: value.return_trigger as ReturnTrigger,
          remarks: value.remarks,
          condition_assessment: value.condition_assessment as ReturnCondition,
          reset_status: value.reset_status as ResetStatus,
        })

        // Step 2 — generate presigned URLs
        setUploadStep('uploading')
        const photoManifest = photos.map((f) => ({
          name: f.name,
          type: 'photo' as const,
          content_type: f.type || 'image/jpeg',
        }))
        const sigManifest = [
          {
            name: 'admin-signature.png',
            type: 'admin-signature' as const,
            content_type: 'image/png',
          },
        ]

        // Use the mutation directly with the fresh returnId (not stale state)
        const { upload_urls } = await generateUrlsMutation.mutateAsync({
          returnId: return_id,
          files: [...photoManifest, ...sigManifest],
        })

        // Step 3 — upload to S3, stop on first failure
        const photoUrls = upload_urls.filter((u) => u.type === 'photo')
        const sigUrl = upload_urls.find((u) => u.type === 'admin-signature')

        if (!sigUrl) throw new Error('No signature URL returned.')

        for (let i = 0; i < photos.length; i++) {
          const res = await fetch(photoUrls[i]?.presigned_url ?? '', {
            method: 'PUT',
            body: photos[i],
            headers: {
              'Content-Type': photoUrls[i]?.content_type ?? photos[i].type,
            },
          })
          if (!res.ok) {
            toast.error(
              res.status === 403
                ? 'Upload session expired. Please close and try again.'
                : 'One or more files failed to upload. Please try again.',
            )
            setUploadStep('form')
            return
          }
        }

        const sigRes = await fetch(sigUrl.presigned_url, {
          method: 'PUT',
          body: sigBlob,
          headers: { 'Content-Type': sigUrl.content_type },
        })
        if (!sigRes.ok) {
          toast.error(
            sigRes.status === 403
              ? 'Upload session expired. Please close and try again.'
              : 'Signature upload failed. Please try again.',
          )
          setUploadStep('form')
          return
        }

        // Step 4 — submit evidence
        setUploadStep('submitting')
        await submitEvidenceMutation.mutateAsync(return_id)

        toast.success('Return initiated. Employee has been notified to sign.')
        setUploadStep('done')
        onSuccess()
      } catch (err) {
        setUploadStep('form')
        if (err instanceof ApiError) {
          if (err.status === 409 && err.message.includes('not in ASSIGNED')) {
            toast.error(err.message)
            onOpenChange(false)
          } else if (err.status === 404) {
            toast.error(err.message)
            onOpenChange(false)
          } else if (err.status === 400) {
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
    if (!open) {
      form.reset()
      setPhotos([])
      setSubmitError(undefined)
      setPhotoError(undefined)
      setSignatureError(undefined)
      setUploadStep('form')
      sigRef.current?.clear()
    }
  }, [open])

  const submitLabel =
    uploadStep === 'initiating'
      ? 'Initiating...'
      : uploadStep === 'uploading'
        ? 'Uploading...'
        : uploadStep === 'submitting'
          ? 'Submitting...'
          : 'Initiate Return'

  return (
    <Dialog open={open} onOpenChange={isPending ? undefined : onOpenChange}>
      <DialogContent className="sm:max-w-2xl md:max-w-3xl lg:max-w-4xl">
        <DialogHeader>
          <DialogTitle>Initiate Asset Return</DialogTitle>
          <DialogDescription>
            Select the return reason, document the asset condition, upload
            photos, and sign.
          </DialogDescription>
        </DialogHeader>

        <div className="overflow-y-auto -mx-1 px-1">
          <form
            id="initiate-return-form"
            onSubmit={(e) => {
              e.preventDefault()
              e.stopPropagation()
              void form.handleSubmit()
            }}
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {/* Left column */}
              <div className="space-y-4">
                <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Purpose of Return
                </p>

                <form.Field
                  name="return_trigger"
                  children={(field) => {
                    const isInvalid =
                      field.state.meta.isTouched && !field.state.meta.isValid
                    return (
                      <Field data-invalid={isInvalid}>
                        <ReturnTriggerSelector
                          value={field.state.value}
                          onChange={(v) => field.handleChange(v)}
                          disabled={isPending}
                        />
                        {isInvalid && (
                          <FieldError errors={field.state.meta.errors} />
                        )}
                      </Field>
                    )
                  }}
                />

                <form.Field
                  name="condition_assessment"
                  children={(field) => {
                    const isInvalid =
                      field.state.meta.isTouched && !field.state.meta.isValid
                    return (
                      <Field data-invalid={isInvalid}>
                        <AssetDetailsCard
                          model={asset.model}
                          serialNumber={asset.serial_number}
                          mode="edit"
                          conditionValue={field.state.value}
                          onConditionChange={(v) => field.handleChange(v)}
                          conditionInvalid={isInvalid}
                        />
                        {isInvalid && (
                          <FieldError errors={field.state.meta.errors} />
                        )}
                      </Field>
                    )
                  }}
                />

                <form.Field
                  name="reset_status"
                  children={(field) => {
                    const isInvalid =
                      field.state.meta.isTouched && !field.state.meta.isValid
                    return (
                      <Field data-invalid={isInvalid}>
                        <FieldLabel htmlFor={field.name}>
                          Reset Status
                        </FieldLabel>
                        <Select
                          value={field.state.value}
                          onValueChange={(v) =>
                            field.handleChange(v as ResetStatus)
                          }
                        >
                          <SelectTrigger
                            id={field.name}
                            aria-invalid={isInvalid}
                            className="w-full"
                          >
                            <SelectValue placeholder="Select reset status..." />
                          </SelectTrigger>
                          <SelectContent>
                            {(
                              Object.keys(ResetStatusLabels) as ResetStatus[]
                            ).map((s) => (
                              <SelectItem key={s} value={s}>
                                {ResetStatusLabels[s]}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
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
                        <FieldLabel htmlFor={field.name}>Remarks</FieldLabel>
                        <Textarea
                          id={field.name}
                          name={field.name}
                          value={field.state.value}
                          onBlur={field.handleBlur}
                          onChange={(e) => field.handleChange(e.target.value)}
                          aria-invalid={isInvalid}
                          placeholder="Describe the asset condition..."
                          rows={3}
                          disabled={isPending}
                        />
                        {isInvalid && (
                          <FieldError errors={field.state.meta.errors} />
                        )}
                      </Field>
                    )
                  }}
                />
              </div>

              {/* Right column */}
              <div className="space-y-4">
                <HandoverTimestampPill
                  label="Return Initiated At"
                  timestamp={timestamp}
                />

                <Field data-invalid={!!photoError}>
                  <FieldLabel>Return Photos</FieldLabel>
                  <EvidencePhotoGrid
                    mode="upload"
                    files={photos}
                    onFilesChange={(files) => {
                      setPhotos(files)
                      if (files.length > 0) setPhotoError(undefined)
                    }}
                  />
                  {photoError && (
                    <FieldError errors={[{ message: photoError }]} />
                  )}
                </Field>

                <Field data-invalid={!!signatureError}>
                  <SignatureCard
                    label="Admin Signature"
                    sigRef={sigRef}
                    onClear={() => sigRef.current?.clear()}
                    disabled={isPending}
                  />
                  {signatureError && (
                    <FieldError errors={[{ message: signatureError }]} />
                  )}
                </Field>
              </div>
            </div>

            {submitError && (
              <div className="alert-danger mt-4">{submitError}</div>
            )}
          </form>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isPending}
          >
            Cancel
          </Button>
          <Button form="initiate-return-form" type="submit" loading={isPending}>
            {submitLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
