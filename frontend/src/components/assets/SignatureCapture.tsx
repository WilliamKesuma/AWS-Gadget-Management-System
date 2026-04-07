import { useRef, useState } from 'react'
import SignatureCanvas from 'react-signature-canvas'

import { Button } from '#/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '#/components/ui/tabs'
import { DragDropZone } from '#/components/assets/DragDropZone'

interface SignatureCaptureProps {
  onSignatureReady: (blob: Blob) => void
  disabled?: boolean
}

export function SignatureCapture({
  onSignatureReady,
  disabled,
}: SignatureCaptureProps) {
  const sigRef = useRef<SignatureCanvas | null>(null)
  const [uploadFiles, setUploadFiles] = useState<File[]>([])

  const handleClear = () => {
    sigRef.current?.clear()
  }

  const handleDrawUpload = () => {
    const canvas = sigRef.current?.getCanvas()
    if (!canvas) return
    canvas.toBlob((blob) => {
      if (blob) onSignatureReady(blob)
    }, 'image/png')
  }

  const handleFileUpload = () => {
    if (uploadFiles.length > 0) {
      onSignatureReady(uploadFiles[0])
    }
  }

  const handleClearFile = () => {
    setUploadFiles([])
  }

  return (
    <Tabs defaultValue="draw" className="w-full">
      <TabsList variant="line" className="w-full">
        <TabsTrigger value="draw">Draw</TabsTrigger>
        <TabsTrigger value="upload">Upload PNG</TabsTrigger>
      </TabsList>

      <TabsContent value="draw" className="space-y-3 pt-3">
        <div className="overflow-hidden rounded-lg border bg-white">
          <SignatureCanvas
            ref={sigRef}
            canvasProps={{
              className: 'w-full h-48',
              style: { width: '100%', height: '192px' },
            }}
            penColor="black"
            backgroundColor="white"
          />
        </div>
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            size="sm"
            onClick={handleClear}
            disabled={disabled}
          >
            Clear
          </Button>
          <Button size="sm" onClick={handleDrawUpload} disabled={disabled}>
            Upload
          </Button>
        </div>
      </TabsContent>

      <TabsContent value="upload" className="space-y-3 pt-3">
        <DragDropZone
          accept="image/png"
          maxFiles={1}
          label="Signature Image (PNG)"
          files={uploadFiles}
          onFilesChange={setUploadFiles}
        />
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            size="sm"
            onClick={handleClearFile}
            disabled={disabled || uploadFiles.length === 0}
          >
            Clear
          </Button>
          <Button
            size="sm"
            onClick={handleFileUpload}
            disabled={disabled || uploadFiles.length === 0}
          >
            Upload
          </Button>
        </div>
      </TabsContent>
    </Tabs>
  )
}
