import { useRef } from 'react'
import { Camera, X } from 'lucide-react'

const MAX_FILES = 10

type UploadProps = {
  mode: 'upload'
  files: File[]
  onFilesChange: (files: File[]) => void
  photoUrls?: never
}

type ReadonlyProps = {
  mode: 'readonly'
  photoUrls: string[]
  files?: never
  onFilesChange?: never
}

type Props = UploadProps | ReadonlyProps

export function EvidencePhotoGrid({
  mode,
  files,
  onFilesChange,
  photoUrls,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  if (mode === 'readonly') {
    if (!photoUrls || photoUrls.length === 0) {
      return (
        <p className="text-sm text-muted-foreground italic">
          No photos uploaded.
        </p>
      )
    }
    return (
      <div className="grid grid-cols-3 gap-2">
        {photoUrls.map((url, i) => (
          <a key={i} href={url} target="_blank" rel="noopener noreferrer">
            <img
              src={url}
              alt={`Return photo ${i + 1}`}
              className="w-full aspect-square object-cover rounded-lg border border-border hover:opacity-80 transition-opacity"
            />
          </a>
        ))}
      </div>
    )
  }

  // upload mode
  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? [])
    const merged = [...(files ?? []), ...selected].slice(0, MAX_FILES)
    onFilesChange(merged)
    // reset so same file can be re-selected
    e.target.value = ''
  }

  const handleRemove = (index: number) => {
    const next = (files ?? []).filter((_, i) => i !== index)
    onFilesChange(next)
  }

  const canAddMore = (files ?? []).length < MAX_FILES

  return (
    <div className="grid grid-cols-3 gap-2">
      {/* Upload tile */}
      {canAddMore && (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="aspect-square flex flex-col items-center justify-center gap-1.5 border-2 border-dashed border-border rounded-lg text-muted-foreground hover:border-primary/50 hover:text-primary transition-colors"
        >
          <Camera className="size-5" />
          <span className="text-xs font-medium">Upload</span>
          <input
            ref={inputRef}
            type="file"
            accept="image/jpeg,image/png"
            multiple
            className="hidden"
            onChange={handleFileInput}
          />
        </button>
      )}

      {/* Preview tiles */}
      {(files ?? []).map((file, i) => {
        const url = URL.createObjectURL(file)
        return (
          <div key={i} className="relative aspect-square group">
            <img
              src={url}
              alt={file.name}
              className="w-full h-full object-cover rounded-lg border border-border"
              onLoad={() => URL.revokeObjectURL(url)}
            />
            <button
              type="button"
              onClick={() => handleRemove(i)}
              className="absolute top-1 right-1 size-5 rounded-full bg-foreground/60 text-background flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <X className="size-3" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
