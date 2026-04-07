import { useState } from 'react'
import { FileIcon, Trash2Icon } from 'lucide-react'
import { Button } from '#/components/ui/button'
import { DragDropZone } from '#/components/assets/DragDropZone'
import { useUploadAsset } from '#/hooks/use-assets'
import { ApiError } from '#/lib/api-client'

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// ─── UploadStep ──────────────────────────────────────────────────────────────

export interface UploadStepProps {
  onUploadComplete: (uploadSessionId: string, scanJobId: string) => void
  onCancel: () => void
}

export function UploadStep({ onUploadComplete, onCancel }: UploadStepProps) {
  const [invoiceFiles, setInvoiceFiles] = useState<File[]>([])
  const [photoFiles, setPhotoFiles] = useState<File[]>([])
  const [invoiceError, setInvoiceError] = useState<string>()
  const [photosError, setPhotosError] = useState<string>()
  const [apiError, setApiError] = useState<string>()

  const uploadAsset = useUploadAsset()

  const allFiles: Array<{ file: File; source: 'invoice' | 'photo' }> = [
    ...invoiceFiles.map((f) => ({ file: f, source: 'invoice' as const })),
    ...photoFiles.map((f) => ({ file: f, source: 'photo' as const })),
  ]

  function removeFile(file: File, source: 'invoice' | 'photo') {
    if (source === 'invoice') {
      setInvoiceFiles((prev) => prev.filter((f) => f !== file))
    } else {
      setPhotoFiles((prev) => prev.filter((f) => f !== file))
    }
  }

  function validate(): boolean {
    let valid = true

    if (invoiceFiles.length === 0) {
      setInvoiceError('Please select an invoice file')
      valid = false
    } else {
      setInvoiceError(undefined)
    }

    if (photoFiles.length === 0) {
      setPhotosError('Please select at least one photo')
      valid = false
    } else if (photoFiles.length > 5) {
      setPhotosError('Maximum 5 photos allowed')
      valid = false
    } else {
      setPhotosError(undefined)
    }

    return valid
  }

  function handleSubmit() {
    setApiError(undefined)
    if (!validate()) return

    uploadAsset.mutate(
      { invoiceFile: invoiceFiles[0], photoFiles },
      {
        onSuccess: (result) => {
          onUploadComplete(result.upload_session_id, result.scan_job_id)
        },
        onError: (err) => {
          setApiError((err as ApiError).message ?? 'Upload failed')
        },
      },
    )
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Drop zones */}
      <div className="flex flex-col gap-4">
        <DragDropZone
          accept="application/pdf,image/*"
          maxFiles={1}
          label="Invoice (PDF or Image)"
          files={invoiceFiles}
          onFilesChange={setInvoiceFiles}
          error={invoiceError}
        />
        <DragDropZone
          accept="image/*"
          maxFiles={5}
          label="Asset Photos (Up to 5)"
          files={photoFiles}
          onFilesChange={setPhotoFiles}
          error={photosError}
        />
      </div>

      {/* Uploaded files list */}
      {allFiles.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Uploaded Files
          </p>
          <div className="flex flex-col gap-1.5">
            {allFiles.map(({ file, source }) => (
              <div
                key={`${source}-${file.name}-${file.size}`}
                className="flex items-center gap-3 rounded-lg border bg-card px-3 py-2"
              >
                <FileIcon className="size-4 shrink-0 text-muted-foreground" />
                <span className="min-w-0 flex-1 break-all text-sm font-medium">
                  {file.name}
                </span>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {formatFileSize(file.size)}
                </span>
                <span className="shrink-0 text-xs text-info">
                  Ready to process
                </span>
                <button
                  type="button"
                  aria-label={`Remove ${file.name}`}
                  onClick={() => removeFile(file, source)}
                  className="shrink-0 rounded p-0.5 text-muted-foreground transition-colors hover:text-danger"
                >
                  <Trash2Icon className="size-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* API error */}
      {apiError && <p className="text-sm text-danger">{apiError}</p>}

      {/* Footer */}
      <div className="flex items-center justify-end gap-3">
        <Button
          variant="outline"
          onClick={onCancel}
          className="text-destructive hover:text-destructive"
        >
          Cancel
        </Button>
        <Button
          variant="default"
          onClick={handleSubmit}
          loading={uploadAsset.isPending}
        >
          Upload &amp; Scan
        </Button>
      </div>
    </div>
  )
}
