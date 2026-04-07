import { useState, useEffect } from 'react'
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
import { Badge } from '#/components/ui/badge'
import { Checkbox } from '#/components/ui/checkbox'
import { Separator } from '#/components/ui/separator'
import { SignatureCapture } from '#/components/assets/SignatureCapture'
import {
  useHandoverForm,
  useSignatureUploadUrl,
  useAcceptHandover,
} from '#/hooks/use-assets'
import { ApiError } from '#/lib/api-client'
import { AssetStatusLabels } from '#/lib/models/labels'
import type { AssetStatus } from '#/lib/models/types'
import { Spinner } from '../ui/spinner'

type AcceptHandoverDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  assetId: string
  asset: {
    brand?: string
    model?: string
    serial_number?: string
    status: AssetStatus
  }
}

export function AcceptHandoverDialog({
  open,
  onOpenChange,
  assetId,
  asset,
}: AcceptHandoverDialogProps) {
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [formViewed, setFormViewed] = useState(false)
  const [reviewChecked, setReviewChecked] = useState(false)
  const [signatureS3Key, setSignatureS3Key] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)

  const handoverForm = useHandoverForm(assetId)
  const signatureUploadUrl = useSignatureUploadUrl(assetId)
  const acceptHandover = useAcceptHandover(assetId)

  // Reset all state when dialog opens/closes
  useEffect(() => {
    setStep(1)
    setFormViewed(false)
    setReviewChecked(false)
    setSignatureS3Key(null)
    setUploading(false)
    handoverForm.reset()
    signatureUploadUrl.reset()
    acceptHandover.reset()
  }, [open])

  const handleDownloadForm = () => {
    handoverForm.mutate(undefined, {
      onSuccess: (data) => {
        window.open(data.presigned_url, '_blank')
        setFormViewed(true)
      },
      onError: (err) => {
        if (err instanceof ApiError) {
          toast.error(err.message)
        } else {
          toast.error('Failed to download handover form. Please try again.')
        }
      },
    })
  }

  const handleSignatureReady = (blob: Blob) => {
    setUploading(true)

    signatureUploadUrl.mutate(undefined, {
      onSuccess: async (data) => {
        try {
          const response = await fetch(data.presigned_url, {
            method: 'PUT',
            body: blob,
            headers: { 'Content-Type': 'image/png' },
          })

          if (response.status === 403) {
            toast.error(
              'This link has expired. Please refresh to get a new one.',
            )
            setUploading(false)
            return
          }

          if (!response.ok) {
            toast.error('Failed to upload signature. Please try again.')
            setUploading(false)
            return
          }

          setSignatureS3Key(data.s3_key)
          setUploading(false)
        } catch {
          toast.error('Failed to upload signature. Please try again.')
          setUploading(false)
        }
      },
      onError: (err) => {
        setUploading(false)
        if (err instanceof ApiError) {
          toast.error(err.message)
        } else {
          toast.error('Failed to get upload URL. Please try again.')
        }
      },
    })
  }

  const handleAccept = () => {
    if (!signatureS3Key) return

    acceptHandover.mutate(
      { signature_s3_key: signatureS3Key },
      {
        onSuccess: () => {
          toast.success('Asset handover accepted successfully.')
          setStep(3)
        },
        onError: (err) => {
          if (err instanceof ApiError) {
            if (
              err.status === 409 &&
              err.message
                .toLowerCase()
                .includes('handover form must be generated')
            ) {
              toast.error(
                `${err.message}. Please contact your IT Admin to generate the handover form.`,
              )
            } else if (
              err.status === 400 &&
              err.message.toLowerCase().includes('signature image not found')
            ) {
              toast.error(
                `${err.message}. Please go back and re-upload your signature.`,
              )
            } else {
              toast.error(err.message)
            }
          } else {
            toast.error('An unexpected error occurred. Please try again.')
          }
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Accept Asset Handover</DialogTitle>
          <DialogDescription>
            {step === 1 && 'Review the asset details and handover form.'}
            {step === 2 && 'Provide your signature to proceed.'}
            {step === 3 && 'Confirm and accept the asset.'}
          </DialogDescription>
        </DialogHeader>

        <div className="overflow-y-auto -mx-1 px-1 space-y-4">
          {/* Step 1 — Review */}
          {step === 1 && (
            <>
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Asset Summary</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <span className="text-muted-foreground">Brand</span>
                  <span>{asset.brand || '—'}</span>
                  <span className="text-muted-foreground">Model</span>
                  <span>{asset.model || '—'}</span>
                  <span className="text-muted-foreground">Serial Number</span>
                  <span>{asset.serial_number || '—'}</span>
                  <span className="text-muted-foreground">Status</span>
                  <span>
                    <Badge variant="info" size="sm">
                      {AssetStatusLabels[asset.status]}
                    </Badge>
                  </span>
                </div>
              </div>

              <Separator />

              <div className="space-y-3">
                <Button
                  variant="outline"
                  onClick={handleDownloadForm}
                  loading={handoverForm.isPending}
                >
                  Download Handover Form
                </Button>

                <div className="flex items-center gap-2">
                  <Checkbox
                    id="review-checkbox"
                    checked={reviewChecked}
                    onCheckedChange={(checked) =>
                      setReviewChecked(checked === true)
                    }
                    disabled={!formViewed}
                  />
                  <label
                    htmlFor="review-checkbox"
                    className="text-sm leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                  >
                    I have read and reviewed the handover form
                  </label>
                </div>
              </div>
            </>
          )}

          {/* Step 2 — Signature */}
          {step === 2 && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium">
                Draw or upload your signature
              </h4>
              <SignatureCapture
                onSignatureReady={handleSignatureReady}
                disabled={uploading}
              />
              {uploading && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Spinner />
                  Uploading signature...
                </div>
              )}
              {signatureS3Key && (
                <div className="text-sm text-info">
                  Signature uploaded successfully.
                </div>
              )}
            </div>
          )}

          {/* Step 3 — Confirm */}
          {step === 3 && (
            <div className="space-y-3">
              {acceptHandover.isSuccess ? (
                <div className="space-y-3">
                  <p className="text-sm">
                    You have successfully accepted this asset. The handover is
                    now complete.
                  </p>
                  {acceptHandover.data?.signed_form_url && (
                    <a
                      href={acceptHandover.data.signed_form_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-primary underline underline-offset-3"
                    >
                      View Signed Handover Form
                    </a>
                  )}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  By clicking "Agree & Accept Asset", you confirm that you have
                  reviewed the handover form and agree to the terms of the asset
                  handover.
                </p>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          {step === 1 && (
            <Button disabled={!reviewChecked} onClick={() => setStep(2)}>
              Next
            </Button>
          )}

          {step === 2 && (
            <>
              <Button variant="outline" onClick={() => setStep(1)}>
                Back
              </Button>
              <Button
                disabled={!signatureS3Key || uploading}
                onClick={() => setStep(3)}
              >
                Next
              </Button>
            </>
          )}

          {step === 3 && !acceptHandover.isSuccess && (
            <>
              <Button
                variant="outline"
                onClick={() => setStep(2)}
                disabled={acceptHandover.isPending}
              >
                Back
              </Button>
              <Button
                disabled={!signatureS3Key || acceptHandover.isPending}
                loading={acceptHandover.isPending}
                onClick={handleAccept}
              >
                Agree & Accept Asset
              </Button>
            </>
          )}

          {step === 3 && acceptHandover.isSuccess && (
            <Button onClick={() => onOpenChange(false)}>Close</Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
