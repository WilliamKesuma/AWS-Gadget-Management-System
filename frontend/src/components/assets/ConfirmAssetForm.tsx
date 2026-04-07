import { useState } from 'react'
import { useNavigate, Link } from '@tanstack/react-router'
import { useForm } from '@tanstack/react-form'
import { z } from 'zod'
import { format as formatISO, parse, isValid } from 'date-fns'
import {
  CalendarIcon,
  ReceiptText,
  Package,
  CreditCard,
  Cpu,
  CheckCircle2Icon,
} from 'lucide-react'
import { Button } from '#/components/ui/button'
import { Input, NumberInput } from '#/components/ui/input'
import { Calendar } from '#/components/ui/calendar'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '#/components/ui/popover'
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
  FieldDescription,
} from '#/components/ui/field'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '#/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '#/components/ui/dialog'
import { Badge } from '#/components/ui/badge'
import { Separator } from '#/components/ui/separator'
import { useCreateAsset } from '#/hooks/use-assets'
import { useAllCategories, formatCategoryName } from '#/hooks/use-categories'
import { ApiError } from '#/lib/api-client'
import { cn, formatDate } from '#/lib/utils'
import {
  type ExtractedFieldValue,
  type CreateAssetRequest,
} from '#/lib/models/types'
import { Textarea } from '../ui/textarea'

// ─── Schema (module scope) ────────────────────────────────────────────────────

const confirmSchema = z.object({
  category: z.string().min(1, 'Required'),
  invoice_number: z.string().min(1, 'Required'),
  vendor: z.string().min(1, 'Required'),
  purchase_date: z.string().min(1, 'Required'),
  brand: z.string().min(1, 'Required'),
  model_name: z.string().min(1, 'Required'),
  cost: z.number().positive('Must be positive'),
  serial_number: z.string(),
  product_description: z.string(),
  payment_method: z.string(),
  processor: z.string(),
  storage: z.string(),
  os_version: z.string(),
  memory: z.string(),
})

// ─── Props ────────────────────────────────────────────────────────────────────

export interface ConfirmAssetFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  scanJobId: string
  uploadSessionId: string
  extractedFields: Record<string, ExtractedFieldValue> | undefined
  /** When set, shows the success step instead of the form */
  successAssetId?: string
}

// ─── Currency parsing helper ──────────────────────────────────────────────────

function parseCurrencyString(raw: string): number {
  const stripped = raw.replace(/[^\d.,]/g, '')
  const dotParts = stripped.split('.')
  if (
    dotParts.length > 2 ||
    (dotParts.length === 2 && dotParts[1].length === 3)
  ) {
    return parseFloat(stripped.replace(/\./g, '').replace(',', '.')) || 0
  }
  return parseFloat(stripped.replace(/,/g, '')) || 0
}

// ─── Confidence helpers ───────────────────────────────────────────────────────

function ConfidenceBadge({ confidence }: { confidence: number | undefined }) {
  if (confidence === undefined) return null
  if (confidence >= 0.8) {
    return <Badge variant="info" size="sm">Confident</Badge>
  }
  return <Badge variant="warning" size="sm">Review</Badge>
}

function AlternativeHint({ value }: { value: string | undefined }) {
  if (!value) return null
  return <FieldDescription>Alternative: {value}</FieldDescription>
}

// ─── Section Header ───────────────────────────────────────────────────────────

function SectionHeader({ icon: Icon, title }: { icon: React.ElementType; title: string }) {
  return (
    <div className="flex items-center gap-2 pt-1">
      <Icon className="size-4 text-muted-foreground" strokeWidth={1.5} />
      <span className="text-sm font-semibold text-foreground">{title}</span>
    </div>
  )
}

// ─── Purchase Date Picker ─────────────────────────────────────────────────────

interface PurchaseDatePickerProps {
  id: string
  value: string
  isInvalid: boolean
  isLowConfidence: boolean
  onSelect: (date: Date | undefined) => void
  onBlur: () => void
}

function PurchaseDatePicker({
  id,
  value,
  isInvalid,
  isLowConfidence,
  onSelect,
  onBlur,
}: PurchaseDatePickerProps) {
  const [open, setOpen] = useState(false)

  let parsedDate: Date | undefined
  if (value) {
    const iso = parse(value, 'yyyy-MM-dd', new Date())
    if (isValid(iso)) {
      parsedDate = iso
    } else {
      const dotFmt = parse(value, 'dd.MM.yyyy', new Date())
      if (isValid(dotFmt)) parsedDate = dotFmt
    }
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id={id}
          variant="outline"
          aria-invalid={isInvalid}
          className={cn(
            'w-full justify-start text-left font-normal',
            !value && 'text-muted-foreground',
            isLowConfidence && 'border-warning',
          )}
          onBlur={onBlur}
        >
          <CalendarIcon className="size-4" />
          {parsedDate ? formatDate(parsedDate) : 'Pick a date'}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={parsedDate}
          onSelect={(date) => {
            onSelect(date)
            setOpen(false)
          }}
          autoFocus
        />
      </PopoverContent>
    </Popover>
  )
}

// ─── SuccessStep ──────────────────────────────────────────────────────────────

function SuccessStep({ assetId }: { assetId: string }) {
  return (
    <div className="flex flex-col items-center gap-6 py-8 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-50">
        <CheckCircle2Icon className="h-8 w-8 text-emerald-600" strokeWidth={1.5} />
      </div>
      <div className="space-y-1">
        <h2 className="text-xl font-semibold text-slate-900">Asset Created</h2>
        <p className="text-sm text-slate-500">
          Asset {assetId} created and pending management approval.
        </p>
      </div>
      <div className="flex gap-3">
        <Button asChild variant="outline">
          <Link to="/assets" search={{}}>Create Another Asset</Link>
        </Button>
        <Button asChild>
          <Link to="/assets" search={{}}>View Asset List</Link>
        </Button>
      </div>
    </div>
  )
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ConfirmAssetForm({
  open,
  onOpenChange,
  scanJobId,
  extractedFields,
  successAssetId,
}: ConfirmAssetFormProps) {
  const navigate = useNavigate()
  const createAsset = useCreateAsset()
  const { data: categoriesData, isLoading: categoriesLoading } = useAllCategories()
  const [submitError, setSubmitError] = useState<string>()

  const form = useForm({
    defaultValues: {
      category: '',
      invoice_number: extractedFields?.['invoice_number']?.value ?? '',
      vendor: extractedFields?.['vendor']?.value ?? '',
      purchase_date: extractedFields?.['purchase_date']?.value ?? '',
      brand: extractedFields?.['brand']?.value ?? '',
      model_name:
        extractedFields?.['model_name']?.value ??
        extractedFields?.['model']?.value ??
        '',
      cost: parseCurrencyString(extractedFields?.['cost']?.value ?? '0'),
      serial_number: extractedFields?.['serial_number']?.value ?? '',
      product_description: extractedFields?.['product_description']?.value ?? '',
      payment_method: extractedFields?.['payment_method']?.value ?? '',
      processor: extractedFields?.['processor']?.value ?? '',
      storage: extractedFields?.['storage']?.value ?? '',
      os_version: extractedFields?.['os_version']?.value ?? '',
      memory: extractedFields?.['memory']?.value ?? '',
    },
    validators: { onSubmit: confirmSchema },
    onSubmit: async ({ value }) => {
      setSubmitError(undefined)
      try {
        const result = await createAsset.mutateAsync({
          ...value,
          scan_job_id: scanJobId,
          category: value.category as CreateAssetRequest['category'],
        })
        void navigate({
          to: '/assets/new',
          search: { asset_id: result.asset_id },
          replace: true,
        })
      } catch (err) {
        setSubmitError((err as ApiError).message)
      }
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={successAssetId ? undefined : 'max-w-2xl flex flex-col'}>
        <DialogHeader>
          <DialogTitle>
            {successAssetId ? 'Asset Created' : 'Confirm Asset Details'}
          </DialogTitle>
          <DialogDescription>
            {successAssetId
              ? 'Your asset has been submitted for management approval.'
              : 'Review the AI-extracted details below and correct any fields before submitting.'}
          </DialogDescription>
        </DialogHeader>

        {successAssetId ? (
          <SuccessStep assetId={successAssetId} />
        ) : (
          <div className="overflow-y-auto flex-1 -mx-1 px-1">
            <form
              onSubmit={(e) => {
                e.preventDefault()
                e.stopPropagation()
                void form.handleSubmit()
              }}
              className="space-y-6"
            >
              {/* ── Section 1: Device Info ──────────────────────────────── */}
              <SectionHeader icon={Package} title="Device Information" />

              <FieldGroup className="grid grid-cols-2">
                {/* Category */}
                <form.Field
                  name="category"
                  children={(field) => {
                    const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid
                    const categories = categoriesData?.items ?? []
                    return (
                      <Field data-invalid={isInvalid}>
                        <FieldLabel htmlFor={field.name}>Category</FieldLabel>
                        <Select
                          name={field.name}
                          value={field.state.value}
                          onValueChange={(val) => field.handleChange(val)}
                          disabled={categoriesLoading}
                        >
                          <SelectTrigger id={field.name} aria-invalid={isInvalid} className="w-full">
                            <SelectValue placeholder={categoriesLoading ? 'Loading…' : 'Select category'} />
                          </SelectTrigger>
                          <SelectContent>
                            {categories.length === 0 && !categoriesLoading ? (
                              <div className="px-2 py-3 text-sm text-muted-foreground text-center">
                                No categories available. Contact management to add categories.
                              </div>
                            ) : (
                              categories.map((cat) => (
                                <SelectItem key={cat.category_id} value={cat.category_name}>
                                  {formatCategoryName(cat.category_name)}
                                </SelectItem>
                              ))
                            )}
                          </SelectContent>
                        </Select>
                        {isInvalid && <FieldError errors={field.state.meta.errors} />}
                      </Field>
                    )
                  }}
                />

                {/* Brand */}
                <form.Field
                  name="brand"
                  children={(field) => {
                    const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid
                    const ef = extractedFields?.['brand']
                    const isLowConfidence = ef?.confidence !== undefined && ef.confidence < 0.8
                    return (
                      <Field data-invalid={isInvalid}>
                        <div className="flex items-center justify-between">
                          <FieldLabel htmlFor={field.name}>Brand</FieldLabel>
                          <ConfidenceBadge confidence={ef?.confidence} />
                        </div>
                        <Input
                          id={field.name}
                          name={field.name}
                          value={field.state.value}
                          onBlur={field.handleBlur}
                          onChange={(e) => field.handleChange(e.target.value)}
                          aria-invalid={isInvalid}
                          className={isLowConfidence ? 'border-warning' : ''}
                        />
                        <AlternativeHint value={ef?.alternative_value} />
                        {isInvalid && <FieldError errors={field.state.meta.errors} />}
                      </Field>
                    )
                  }}
                />

                {/* Model Name */}
                <form.Field
                  name="model_name"
                  children={(field) => {
                    const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid
                    const ef = extractedFields?.['model_name'] ?? extractedFields?.['model']
                    const isLowConfidence = ef?.confidence !== undefined && ef.confidence < 0.8
                    return (
                      <Field data-invalid={isInvalid}>
                        <div className="flex items-center justify-between">
                          <FieldLabel htmlFor={field.name}>Model Name</FieldLabel>
                          <ConfidenceBadge confidence={ef?.confidence} />
                        </div>
                        <Input
                          id={field.name}
                          name={field.name}
                          value={field.state.value}
                          onBlur={field.handleBlur}
                          onChange={(e) => field.handleChange(e.target.value)}
                          aria-invalid={isInvalid}
                          className={isLowConfidence ? 'border-warning' : ''}
                        />
                        <AlternativeHint value={ef?.alternative_value} />
                        {isInvalid && <FieldError errors={field.state.meta.errors} />}
                      </Field>
                    )
                  }}
                />

                {/* Serial Number */}
                <form.Field
                  name="serial_number"
                  children={(field) => {
                    const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid
                    const ef = extractedFields?.['serial_number']
                    const isLowConfidence = ef?.confidence !== undefined && ef.confidence < 0.8
                    return (
                      <Field data-invalid={isInvalid}>
                        <div className="flex items-center justify-between">
                          <FieldLabel htmlFor={field.name}>Serial Number</FieldLabel>
                          <ConfidenceBadge confidence={ef?.confidence} />
                        </div>
                        <Input
                          id={field.name}
                          name={field.name}
                          value={field.state.value ?? ''}
                          onBlur={field.handleBlur}
                          onChange={(e) => field.handleChange(e.target.value)}
                          aria-invalid={isInvalid}
                          className={isLowConfidence ? 'border-warning' : ''}
                        />
                        <AlternativeHint value={ef?.alternative_value} />
                        {isInvalid && <FieldError errors={field.state.meta.errors} />}
                      </Field>
                    )
                  }}
                />

                {/* Product Description — full width */}
                <form.Field
                  name="product_description"
                  children={(field) => {
                    const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid
                    const ef = extractedFields?.['product_description']
                    const isLowConfidence = ef?.confidence !== undefined && ef.confidence < 0.8
                    return (
                      <Field data-invalid={isInvalid} className="col-span-2">
                        <div className="flex items-center justify-between">
                          <FieldLabel htmlFor={field.name}>Product Description</FieldLabel>
                          <ConfidenceBadge confidence={ef?.confidence} />
                        </div>
                        <Textarea
                          id={field.name}
                          name={field.name}
                          value={field.state.value ?? ''}
                          onBlur={field.handleBlur}
                          onChange={(e) => field.handleChange(e.target.value)}
                          aria-invalid={isInvalid}
                          className={isLowConfidence ? 'border-warning' : ''}
                        />
                        <AlternativeHint value={ef?.alternative_value} />
                        {isInvalid && <FieldError errors={field.state.meta.errors} />}
                      </Field>
                    )
                  }}
                />
              </FieldGroup>

              <Separator />

              {/* ── Section 2: Purchase & Invoice ──────────────────────── */}
              <SectionHeader icon={ReceiptText} title="Purchase & Invoice" />

              <FieldGroup className="grid grid-cols-2">
                {/* Invoice Number */}
                <form.Field
                  name="invoice_number"
                  children={(field) => {
                    const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid
                    const ef = extractedFields?.['invoice_number']
                    const isLowConfidence = ef?.confidence !== undefined && ef.confidence < 0.8
                    return (
                      <Field data-invalid={isInvalid}>
                        <div className="flex items-center justify-between">
                          <FieldLabel htmlFor={field.name}>Invoice Number</FieldLabel>
                          <ConfidenceBadge confidence={ef?.confidence} />
                        </div>
                        <Input
                          id={field.name}
                          name={field.name}
                          value={field.state.value}
                          onBlur={field.handleBlur}
                          onChange={(e) => field.handleChange(e.target.value)}
                          aria-invalid={isInvalid}
                          className={isLowConfidence ? 'border-warning' : ''}
                        />
                        <AlternativeHint value={ef?.alternative_value} />
                        {isInvalid && <FieldError errors={field.state.meta.errors} />}
                      </Field>
                    )
                  }}
                />

                {/* Vendor */}
                <form.Field
                  name="vendor"
                  children={(field) => {
                    const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid
                    const ef = extractedFields?.['vendor']
                    const isLowConfidence = ef?.confidence !== undefined && ef.confidence < 0.8
                    return (
                      <Field data-invalid={isInvalid}>
                        <div className="flex items-center justify-between">
                          <FieldLabel htmlFor={field.name}>Vendor</FieldLabel>
                          <ConfidenceBadge confidence={ef?.confidence} />
                        </div>
                        <Input
                          id={field.name}
                          name={field.name}
                          value={field.state.value}
                          onBlur={field.handleBlur}
                          onChange={(e) => field.handleChange(e.target.value)}
                          aria-invalid={isInvalid}
                          className={isLowConfidence ? 'border-warning' : ''}
                        />
                        <AlternativeHint value={ef?.alternative_value} />
                        {isInvalid && <FieldError errors={field.state.meta.errors} />}
                      </Field>
                    )
                  }}
                />

                {/* Purchase Date */}
                <form.Field
                  name="purchase_date"
                  children={(field) => {
                    const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid
                    const ef = extractedFields?.['purchase_date']
                    const isLowConfidence = ef?.confidence !== undefined && ef.confidence < 0.8
                    return (
                      <Field data-invalid={isInvalid}>
                        <div className="flex items-center justify-between">
                          <FieldLabel htmlFor={field.name}>Purchase Date</FieldLabel>
                          <ConfidenceBadge confidence={ef?.confidence} />
                        </div>
                        <PurchaseDatePicker
                          id={field.name}
                          value={field.state.value}
                          isInvalid={isInvalid}
                          isLowConfidence={isLowConfidence}
                          onSelect={(date) =>
                            field.handleChange(date ? formatISO(date, 'yyyy-MM-dd') : '')
                          }
                          onBlur={field.handleBlur}
                        />
                        <AlternativeHint value={ef?.alternative_value} />
                        {isInvalid && <FieldError errors={field.state.meta.errors} />}
                      </Field>
                    )
                  }}
                />
              </FieldGroup>

              <Separator />

              {/* ── Section 3: Cost & Payment ──────────────────────────── */}
              <SectionHeader icon={CreditCard} title="Cost & Payment" />

              <FieldGroup className="grid grid-cols-2">
                {/* Cost */}
                <form.Field
                  name="cost"
                  children={(field) => {
                    const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid
                    const ef = extractedFields?.['cost']
                    const isLowConfidence = ef?.confidence !== undefined && ef.confidence < 0.8
                    return (
                      <Field data-invalid={isInvalid}>
                        <div className="flex items-center justify-between">
                          <FieldLabel htmlFor={field.name}>Cost</FieldLabel>
                          <ConfidenceBadge confidence={ef?.confidence} />
                        </div>
                        <NumberInput
                          id={field.name}
                          value={field.state.value}
                          onChange={(v) => field.handleChange(v ?? 0)}
                          onBlur={field.handleBlur}
                          aria-invalid={isInvalid}
                          placeholder="0"
                          className={isLowConfidence ? 'border-warning' : ''}
                        />
                        <AlternativeHint value={ef?.alternative_value} />
                        {isInvalid && <FieldError errors={field.state.meta.errors} />}
                      </Field>
                    )
                  }}
                />

                {/* Payment Method */}
                <form.Field
                  name="payment_method"
                  children={(field) => {
                    const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid
                    const ef = extractedFields?.['payment_method']
                    const isLowConfidence = ef?.confidence !== undefined && ef.confidence < 0.8
                    return (
                      <Field data-invalid={isInvalid}>
                        <div className="flex items-center justify-between">
                          <FieldLabel htmlFor={field.name}>Payment Method</FieldLabel>
                          <ConfidenceBadge confidence={ef?.confidence} />
                        </div>
                        <Input
                          id={field.name}
                          name={field.name}
                          value={field.state.value ?? ''}
                          onBlur={field.handleBlur}
                          onChange={(e) => field.handleChange(e.target.value)}
                          aria-invalid={isInvalid}
                          className={isLowConfidence ? 'border-warning' : ''}
                        />
                        <AlternativeHint value={ef?.alternative_value} />
                        {isInvalid && <FieldError errors={field.state.meta.errors} />}
                      </Field>
                    )
                  }}
                />
              </FieldGroup>

              <Separator />

              {/* ── Section 4: Technical Specs ─────────────────────────── */}
              <SectionHeader icon={Cpu} title="Technical Specs" />

              <FieldGroup className="grid grid-cols-2">
                {/* Processor */}
                <form.Field
                  name="processor"
                  children={(field) => {
                    const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid
                    const ef = extractedFields?.['processor']
                    const isLowConfidence = ef?.confidence !== undefined && ef.confidence < 0.8
                    return (
                      <Field data-invalid={isInvalid}>
                        <div className="flex items-center justify-between">
                          <FieldLabel htmlFor={field.name}>Processor</FieldLabel>
                          <ConfidenceBadge confidence={ef?.confidence} />
                        </div>
                        <Input
                          id={field.name}
                          name={field.name}
                          value={field.state.value ?? ''}
                          onBlur={field.handleBlur}
                          onChange={(e) => field.handleChange(e.target.value)}
                          aria-invalid={isInvalid}
                          placeholder="e.g. Intel Core i7-1165G7"
                          className={isLowConfidence ? 'border-warning' : ''}
                        />
                        <AlternativeHint value={ef?.alternative_value} />
                        {isInvalid && <FieldError errors={field.state.meta.errors} />}
                      </Field>
                    )
                  }}
                />

                {/* Memory */}
                <form.Field
                  name="memory"
                  children={(field) => {
                    const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid
                    const ef = extractedFields?.['memory']
                    const isLowConfidence = ef?.confidence !== undefined && ef.confidence < 0.8
                    return (
                      <Field data-invalid={isInvalid}>
                        <div className="flex items-center justify-between">
                          <FieldLabel htmlFor={field.name}>Memory (RAM)</FieldLabel>
                          <ConfidenceBadge confidence={ef?.confidence} />
                        </div>
                        <Input
                          id={field.name}
                          name={field.name}
                          value={field.state.value ?? ''}
                          onBlur={field.handleBlur}
                          onChange={(e) => field.handleChange(e.target.value)}
                          aria-invalid={isInvalid}
                          placeholder="e.g. 16GB DDR4"
                          className={isLowConfidence ? 'border-warning' : ''}
                        />
                        <AlternativeHint value={ef?.alternative_value} />
                        {isInvalid && <FieldError errors={field.state.meta.errors} />}
                      </Field>
                    )
                  }}
                />

                {/* Storage */}
                <form.Field
                  name="storage"
                  children={(field) => {
                    const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid
                    const ef = extractedFields?.['storage']
                    const isLowConfidence = ef?.confidence !== undefined && ef.confidence < 0.8
                    return (
                      <Field data-invalid={isInvalid}>
                        <div className="flex items-center justify-between">
                          <FieldLabel htmlFor={field.name}>Storage</FieldLabel>
                          <ConfidenceBadge confidence={ef?.confidence} />
                        </div>
                        <Input
                          id={field.name}
                          name={field.name}
                          value={field.state.value ?? ''}
                          onBlur={field.handleBlur}
                          onChange={(e) => field.handleChange(e.target.value)}
                          aria-invalid={isInvalid}
                          placeholder="e.g. 512GB SSD"
                          className={isLowConfidence ? 'border-warning' : ''}
                        />
                        <AlternativeHint value={ef?.alternative_value} />
                        {isInvalid && <FieldError errors={field.state.meta.errors} />}
                      </Field>
                    )
                  }}
                />

                {/* OS Version */}
                <form.Field
                  name="os_version"
                  children={(field) => {
                    const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid
                    const ef = extractedFields?.['os_version']
                    const isLowConfidence = ef?.confidence !== undefined && ef.confidence < 0.8
                    return (
                      <Field data-invalid={isInvalid}>
                        <div className="flex items-center justify-between">
                          <FieldLabel htmlFor={field.name}>OS Version</FieldLabel>
                          <ConfidenceBadge confidence={ef?.confidence} />
                        </div>
                        <Input
                          id={field.name}
                          name={field.name}
                          value={field.state.value ?? ''}
                          onBlur={field.handleBlur}
                          onChange={(e) => field.handleChange(e.target.value)}
                          aria-invalid={isInvalid}
                          placeholder="e.g. Windows 11 Pro"
                          className={isLowConfidence ? 'border-warning' : ''}
                        />
                        <AlternativeHint value={ef?.alternative_value} />
                        {isInvalid && <FieldError errors={field.state.meta.errors} />}
                      </Field>
                    )
                  }}
                />
              </FieldGroup>

              {/* Submit error */}
              {submitError && <div className="alert-danger">{submitError}</div>}
            </form>
          </div>
        )}
        {!successAssetId && (
          <DialogFooter>
            {/* Submit button */}
            <form.Subscribe selector={(state) => state.canSubmit}>
              {(canSubmit) => (
                <Button
                  type="button"
                  disabled={!canSubmit}
                  loading={createAsset.isPending}
                  onClick={() => form.handleSubmit()}
                  className="w-full"
                >
                  Submit Asset
                </Button>
              )}
            </form.Subscribe>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}
