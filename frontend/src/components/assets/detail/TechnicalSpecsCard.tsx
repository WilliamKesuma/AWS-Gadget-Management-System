import { Cpu, HardDrive, MemoryStick, Monitor } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '#/components/ui/card'
import { Separator } from '#/components/ui/separator'
import type { GetAssetResponse } from '#/lib/models/types'

function SpecField({ label, value }: { label: string; value?: string }) {
  if (!value) return null
  return (
    <div className="space-y-0.5">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-medium">{value}</p>
    </div>
  )
}

export function TechnicalSpecsCard({ asset }: { asset: GetAssetResponse }) {
  const hasHardware =
    asset.processor || asset.memory || asset.storage || asset.os_version
  const hasIdentifiers = asset.serial_number || asset.product_description

  if (!hasHardware && !hasIdentifiers) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <Cpu className="size-4 text-muted-foreground" strokeWidth={1.5} />
          Technical Specifications
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {hasHardware && (
          <div className="grid grid-cols-2 gap-x-6 gap-y-3">
            {asset.processor && (
              <div className="space-y-0.5">
                <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                  <Cpu className="size-3" />
                  Processor
                </p>
                <p className="text-sm font-medium">{asset.processor}</p>
              </div>
            )}
            {asset.memory && (
              <div className="space-y-0.5">
                <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                  <MemoryStick className="size-3" />
                  Memory
                </p>
                <p className="text-sm font-medium">{asset.memory}</p>
              </div>
            )}
            {asset.storage && (
              <div className="space-y-0.5">
                <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                  <HardDrive className="size-3" />
                  Storage
                </p>
                <p className="text-sm font-medium">{asset.storage}</p>
              </div>
            )}
            {asset.os_version && (
              <div className="space-y-0.5">
                <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                  <Monitor className="size-3" />
                  OS Version
                </p>
                <p className="text-sm font-medium">{asset.os_version}</p>
              </div>
            )}
          </div>
        )}

        {hasHardware && hasIdentifiers && <Separator />}

        {hasIdentifiers && (
          <div className="grid grid-cols-2 gap-x-6 gap-y-3">
            <SpecField label="Serial Number" value={asset.serial_number} />
            <SpecField label="Description" value={asset.product_description} />
          </div>
        )}
      </CardContent>
    </Card>
  )
}
