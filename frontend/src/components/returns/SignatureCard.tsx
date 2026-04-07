import type { RefObject } from 'react'
import SignatureCanvas from 'react-signature-canvas'
import { Button } from '#/components/ui/button'

type Props = {
  label: string
  idLabel?: string
  onClear: () => void
  sigRef: RefObject<SignatureCanvas | null>
  disabled?: boolean
}

export function SignatureCard({
  label,
  idLabel,
  onClear,
  sigRef,
  disabled,
}: Props) {
  return (
    <div className="border border-border rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-muted/30">
        <span className="text-[11px] font-bold uppercase tracking-wider text-info">
          {label}
        </span>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-6 px-2 text-xs"
          onClick={onClear}
          disabled={disabled}
        >
          Clear
        </Button>
      </div>

      {/* Canvas */}
      <div className="relative bg-white h-[200px]">
        <SignatureCanvas
          ref={sigRef}
          canvasProps={{
            className: 'w-full h-full',
            style: { width: '100%', height: '200px' },
          }}
          penColor="black"
          backgroundColor="white"
        />
        {idLabel && (
          <span className="absolute bottom-2 right-3 text-[10px] text-muted-foreground select-none">
            {idLabel}
          </span>
        )}
      </div>
    </div>
  )
}
