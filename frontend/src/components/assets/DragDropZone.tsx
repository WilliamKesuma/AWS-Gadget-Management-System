import { useRef, useState } from 'react'
import { FileIcon, UploadCloudIcon, XIcon } from 'lucide-react'

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function isMimeAccepted(file: File, accept: string): boolean {
  const acceptedTypes = accept.split(',').map((t) => t.trim())
  return acceptedTypes.some((type) => {
    if (type.endsWith('/*')) {
      const category = type.split('/')[0]
      return file.type.startsWith(`${category}/`)
    }
    return file.type === type
  })
}

// ─── DragDropZone ────────────────────────────────────────────────────────────

export interface DragDropZoneProps {
  accept: string
  maxFiles: number
  label: string
  files: File[]
  onFilesChange: (files: File[]) => void
  error?: string
}

export function DragDropZone({
  accept,
  maxFiles,
  label,
  files,
  onFilesChange,
  error,
}: DragDropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)

  function handleFiles(incoming: FileList | null) {
    if (!incoming) return
    const valid = Array.from(incoming).filter((f) => isMimeAccepted(f, accept))
    if (maxFiles === 1) {
      onFilesChange(valid.slice(0, 1))
    } else {
      const merged = [...files, ...valid].slice(0, maxFiles)
      onFilesChange(merged)
    }
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault()
    setIsDragging(true)
  }

  function handleDragLeave() {
    setIsDragging(false)
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setIsDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  return (
    <div className="flex flex-col gap-1.5">
      <div
        role="button"
        tabIndex={0}
        aria-label={`Upload ${label}`}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={[
          'flex min-h-[120px] cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-4 transition-colors',
          isDragging
            ? 'border-primary bg-primary/5'
            : 'border-border bg-muted/30 hover:bg-muted/50',
          error ? 'border-danger' : '',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={maxFiles > 1}
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <UploadCloudIcon className="size-8 text-muted-foreground" />
        <div className="text-center">
          <p className="text-sm font-medium">{label}</p>
          <p className="text-xs text-muted-foreground">
            Click to browse or drag &amp; drop
          </p>
        </div>
        {files.length > 0 && (
          <div className="mt-1 flex w-full flex-col gap-1">
            {files.map((file, idx) => (
              <div
                key={`${file.name}-${file.size}`}
                className="flex items-center gap-2 rounded-md bg-background px-3 py-1.5 text-xs"
              >
                <FileIcon className="size-3.5 shrink-0 text-muted-foreground" />
                <span className="min-w-0 flex-1 break-all font-medium">
                  {file.name}
                </span>
                <span className="shrink-0 text-muted-foreground">
                  {formatFileSize(file.size)}
                </span>
                <span className="shrink-0 text-info">Ready to process</span>
                <button
                  type="button"
                  aria-label={`Remove ${file.name}`}
                  onClick={(e) => {
                    e.stopPropagation()
                    onFilesChange(files.filter((_, i) => i !== idx))
                  }}
                  className="shrink-0 rounded-sm p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  <XIcon className="size-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  )
}
