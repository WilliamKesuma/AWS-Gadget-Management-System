import { ReceiptText, CreditCard, Download } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '#/components/ui/card'
import { Button } from '#/components/ui/button'
import { Separator } from '#/components/ui/separator'
import type { GetAssetResponse } from '#/lib/models/types'
import { formatDate, formatNumber } from '#/lib/utils'

function DetailField({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-0.5">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-medium">{children}</p>
    </div>
  )
}

export function PurchaseInvoiceCard({ asset }: { asset: GetAssetResponse }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <ReceiptText
            className="size-4 text-muted-foreground"
            strokeWidth={1.5}
          />
          Purchase &amp; Invoice
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-x-6 gap-y-3">
          <DetailField label="Invoice Number">
            {asset.invoice_number ?? '—'}
          </DetailField>
          <DetailField label="Vendor">{asset.vendor ?? '—'}</DetailField>
          <DetailField label="Purchase Date">
            {formatDate(asset.purchase_date) || '—'}
          </DetailField>
        </div>

        <Separator />

        <div className="flex items-center gap-2 text-sm font-semibold">
          <CreditCard
            className="size-4 text-muted-foreground"
            strokeWidth={1.5}
          />
          Cost &amp; Payment
        </div>
        <div className="grid grid-cols-2 gap-x-6 gap-y-3">
          <DetailField label="Cost">
            {asset.cost != null ? formatNumber(asset.cost) : '—'}
          </DetailField>
          <DetailField label="Payment Method">
            {asset.payment_method ?? '—'}
          </DetailField>
        </div>

        {asset.invoice_url && (
          <>
            <Separator />
            <Button variant="outline" size="sm" asChild>
              <a
                href={asset.invoice_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Download className="size-3 mr-1.5" />
                View / Download Invoice
              </a>
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  )
}
