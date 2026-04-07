import { useRef, useState } from 'react'
import { toast } from 'sonner'
import { useNavigate } from '@tanstack/react-router'
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
import { ReturnTriggerDisplay } from './ReturnTriggerDisplay'
import { AssetDetailsCard } from './AssetDetailsCard'
import { HandoverTimestampPill } from './HandoverTimestampPill'
import { EvidencePhotoGrid } from './EvidencePhotoGrid'
import { SignatureCard } from './SignatureCard'
import {
  useGenerateReturnSignatureUploadUrl,
  useCompleteReturn,
} from '#/hooks/use-returns'
import { ApiError } from '#/lib/api-client'
import type { GetReturnResponse } from '#/lib/models/types'

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  assetId: string
  returnId: string
  returnData: GetReturnResponse
  employeeName: string
  onSuccess: () => void
}

export function EmployeeSignatureDialog({
  open,
  onOpenChange,
  assetId,
  returnId,
  returnData,
  employeeName,
  onSuccess,
}: Props) {
  const navigate = useNavigate()
  const sigRef = useRef<SignatureCanvas | null>(null)
  const [isPending, setIsPending] = useState(false)

  const generateSigUrlMutation = useGenerateReturnSignatureUploadUrl(
    assetId,
    returnId,
  )
  const completeReturnMutation = useCompleteReturn(assetId, returnId)

  async function handleComplete() {
    const canvas = sigRef.current
    if (!canvas || canvas.isEmpty()) {
      toast.error('Please draw your signature before completing the return.')
      return
    }

    setIsPending(true)
    try {
      // Export signature as PNG blob
      const sigBlob = await new Promise<Blob>((resolve, reject) => {
        canvas.getCanvas().toBlob((blob) => {
          if (blob) resolve(blob)
          else reject(new Error('Failed to export signature.'))
        }, 'image/png')
      })

      // Get presigned upload URL
      const { presigned_url, s3_key } =
        await generateSigUrlMutation.mutateAsync()

      // Upload to S3
      const uploadRes = await fetch(presigned_url, {
        method: 'PUT',
        body: sigBlob,
        headers: { 'Content-Type': 'image/png' },
      })

      if (uploadRes.status === 403) {
        toast.error('Upload session expired. Please refresh and try again.')
        return
      }
      if (!uploadRes.ok) {
        toast.error('Failed to upload signature. Please try again.')
        return
      }

      // Complete the return
      await completeReturnMutation.mutateAsync({
        user_signature_s3_key: s3_key,
      })
      toast.success('Return completed successfully.')
      onSuccess()
      onOpenChange(false)
      void navigate({ to: '/' })
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(err.message)
      } else {
        toast.error('An unexpected error occurred. Please try again.')
      }
    } finally {
      setIsPending(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={isPending ? undefined : onOpenChange}>
      <DialogContent className="sm:max-w-2xl md:max-w-3xl lg:max-w-4xl">
        <DialogHeader>
          <DialogTitle>Sign &amp; Complete Return</DialogTitle>
          <DialogDescription>
            Review the return details and provide your signature to complete the
            process.
          </DialogDescription>
        </DialogHeader>

        <div className="overflow-y-auto -mx-1 px-1">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {/* Left column — read-only summary */}
            <div className="space-y-4">
              <ReturnTriggerDisplay trigger={returnData.return_trigger} />

              <AssetDetailsCard
                model={returnData.model}
                serialNumber={returnData.serial_number}
                mode="readonly"
                conditionValue={returnData.condition_assessment}
              />

              {returnData.remarks && (
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1.5">
                    Remarks
                  </p>
                  <p className="text-sm bg-muted/30 rounded-lg p-3 min-h-[80px]">
                    {returnData.remarks}
                  </p>
                </div>
              )}
            </div>

            {/* Right column — evidence + signature */}
            <div className="space-y-4">
              <HandoverTimestampPill
                label="Return Timestamp"
                timestamp={returnData.initiated_at}
              />

              {returnData.return_photo_urls &&
                returnData.return_photo_urls.length > 0 && (
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">
                      Return Photos
                    </p>
                    <EvidencePhotoGrid
                      mode="readonly"
                      photoUrls={returnData.return_photo_urls}
                    />
                  </div>
                )}

              <SignatureCard
                label={`User Signature (${employeeName.toUpperCase()})`}
                sigRef={sigRef}
                onClear={() => sigRef.current?.clear()}
                disabled={isPending}
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isPending}
          >
            Cancel
          </Button>
          <Button onClick={handleComplete} loading={isPending}>
            Complete Return
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
