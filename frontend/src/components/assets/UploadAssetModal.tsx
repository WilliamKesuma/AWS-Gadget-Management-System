import { useEffect, useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '#/components/ui/dialog'
import { UploadStep } from '#/components/assets/UploadStep'
import { PollingStep } from '#/components/assets/PollingStep'

export interface UploadAssetModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function UploadAssetModal({
  open,
  onOpenChange,
}: UploadAssetModalProps) {
  const [step, setStep] = useState<'upload' | 'polling'>('upload')
  const [uploadSessionId, setUploadSessionId] = useState<string | null>(null)
  const [scanJobId, setScanJobId] = useState<string | null>(null)

  useEffect(() => {
    if (!open) {
      setStep('upload')
      setUploadSessionId(null)
      setScanJobId(null)
    }
  }, [open])

  function handleUploadComplete(
    newUploadSessionId: string,
    newScanJobId: string,
  ) {
    setUploadSessionId(newUploadSessionId)
    setScanJobId(newScanJobId)
    setStep('polling')
  }

  function handleRetry() {
    setStep('upload')
    setUploadSessionId(null)
    setScanJobId(null)
  }

  function handleCancel() {
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload New Asset</DialogTitle>
          <DialogDescription>
            Upload an invoice and gadget photo to auto-extract asset details.
          </DialogDescription>
        </DialogHeader>
        {step === 'upload' ? (
          <UploadStep
            onUploadComplete={handleUploadComplete}
            onCancel={handleCancel}
          />
        ) : (
          <PollingStep
            scanJobId={scanJobId!}
            uploadSessionId={uploadSessionId!}
            onCancel={handleCancel}
            onRetry={handleRetry}
          />
        )}
      </DialogContent>
    </Dialog>
  )
}
