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
import { DragDropZone } from '#/components/assets/DragDropZone'
import { useGenerateIssueUploadUrls } from '#/hooks/use-issues'
import { ApiError } from '#/lib/api-client'

type UploadIssuePhotosDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  assetId: string
  timestamp: string
}

export function UploadIssuePhotosDialog({
  open,
  onOpenChange,
  assetId,
  timestamp,
}: UploadIssuePhotosDialogProps) {
  const uploadUrlsMutation = useGenerateIssueUploadUrls(assetId, timestamp)
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [inlineError, setInlineError] = useState<string>()

  useEffect(() => {
    setFiles([])
    setUploading(false)
    setInlineError(undefined)
  }, [open])

  const handleUpload = async () => {
    if (files.length === 0) return
    setInlineError(undefined)
    setUploading(true)

    try {
      const manifest = files.map((f) => ({
        name: f.name,
        type: 'photo' as const,
        content_type: f.type,
      }))
      const response = await uploadUrlsMutation.mutateAsync({ files: manifest })

      for (let i = 0; i < response.upload_urls.length; i++) {
        const urlItem = response.upload_urls[i]
        const res = await fetch(urlItem.presigned_url, {
          method: 'PUT',
          body: files[i],
          headers: { 'Content-Type': urlItem.content_type },
        })
        if (!res.ok) {
          toast.error(
            res.status === 403
              ? 'Upload session expired. Please try again.'
              : 'One or more photo uploads failed. Please try again.',
          )
          return
        }
      }

      toast.success('Photos uploaded successfully.')
      onOpenChange(false)
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setInlineError(err.message)
      } else {
        toast.error('An unexpected error occurred. Please try again.')
      }
    } finally {
      setUploading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload Evidence Photos</DialogTitle>
          <DialogDescription>
            Attach photos of the issue to help IT Admin diagnose the problem.
          </DialogDescription>
        </DialogHeader>

        <div className="overflow-y-auto -mx-1 px-1">
          <DragDropZone
            accept="image/jpeg,image/png"
            maxFiles={5}
            label="Click to upload or drag and drop — PNG, JPG (max. 10MB)"
            files={files}
            onFilesChange={setFiles}
          />
          {inlineError && (
            <div className="alert-danger mt-4">{inlineError}</div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Skip
          </Button>
          <Button
            onClick={() => void handleUpload()}
            disabled={files.length === 0 || uploading}
            loading={uploading}
          >
            Upload Photos
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
