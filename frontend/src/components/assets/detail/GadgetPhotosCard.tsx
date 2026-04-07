import { useState } from 'react'
import { ImageIcon } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '#/components/ui/card'
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselPrevious,
  CarouselNext,
} from '#/components/ui/carousel'

function PresignedImage({ src, alt }: { src: string; alt: string }) {
  const [failed, setFailed] = useState(false)

  if (failed) {
    return (
      <div className="flex flex-col items-center justify-center h-64 bg-muted rounded-lg gap-2">
        <ImageIcon className="size-8 text-muted-foreground" />
        <p className="text-xs text-muted-foreground">Image failed to load</p>
      </div>
    )
  }

  return (
    <img
      src={src}
      alt={alt}
      className="w-full h-64 object-contain rounded-lg bg-muted"
      onError={() => setFailed(true)}
    />
  )
}

export function GadgetPhotosCard({
  assetId,
  photoUrls,
}: {
  assetId: string
  photoUrls: string[]
}) {
  if (photoUrls.length === 0) return null

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-sm">
          <ImageIcon
            className="size-4 text-muted-foreground"
            strokeWidth={1.5}
          />
          Gadget Photos
        </CardTitle>
      </CardHeader>
      <CardContent>
        {photoUrls.length === 1 ? (
          <PresignedImage src={photoUrls[0]} alt={`${assetId} photo`} />
        ) : (
          <div className="px-12">
            <Carousel opts={{ loop: true }}>
              <CarouselContent>
                {photoUrls.map((url, i) => (
                  <CarouselItem key={i}>
                    <PresignedImage
                      src={url}
                      alt={`${assetId} photo ${i + 1}`}
                    />
                  </CarouselItem>
                ))}
              </CarouselContent>
              <CarouselPrevious />
              <CarouselNext />
            </Carousel>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
