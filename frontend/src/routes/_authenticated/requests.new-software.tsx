import {
  createFileRoute,
  redirect,
  useNavigate,
  Link,
} from '@tanstack/react-router'
import { useMemo, useState } from 'react'
import { useForm } from '@tanstack/react-form'
import { z } from 'zod'
import { toast } from 'sonner'
import {
  DataAccessImpactSchema,
  type DataAccessImpact,
} from '#/lib/models/types'
import { useAssets } from '#/hooks/use-assets'
import { useSubmitSoftwareRequest } from '#/hooks/use-software-requests'
import { ApiError } from '#/lib/api-client'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { Textarea } from '#/components/ui/textarea'
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '#/components/ui/field'
import {
  Autocomplete,
  type AutocompleteOption,
} from '#/components/ui/autocomplete'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '#/components/ui/select'
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '#/components/ui/breadcrumb'
import {
  getBaseMeta,
  getPageMeta,
  getCanonicalLink,
  type SeoPageInput,
} from '../../lib/seo'
import { hasRole } from '#/lib/permissions'
import { DataAccessImpactLabels } from '#/lib/models/labels'

const NEW_SOFTWARE_SEO = {
  title: 'Request Software Installation',
  description:
    'Submit a software installation request for your assigned device. IT Admin will review and process it.',
  path: '/requests/new-software',
} satisfies SeoPageInput

const softwareFormSchema = z.object({
  asset_id: z.string().min(1, 'Please select an assigned device.'),
  software_name: z.string().min(1, 'Software name is required.'),
  version: z.string().min(1, 'Version is required.'),
  vendor: z.string().min(1, 'Vendor is required.'),
  justification: z.string().min(1, 'Justification is required.'),
  license_type: z.string().min(1, 'License type is required.'),
  license_validity_period: z
    .string()
    .min(1, 'License validity period is required.'),
  data_access_impact: DataAccessImpactSchema,
})

export const Route = createFileRoute('/_authenticated/requests/new-software')({
  beforeLoad: ({ context }) => {
    if (!hasRole(context.userRole, ['employee'])) {
      throw redirect({ to: '/unauthorized' })
    }
  },
  component: NewSoftwareRequestPage,
  head: () => ({
    meta: [
      ...getBaseMeta(),
      { name: 'robots', content: 'noindex, nofollow' },
      ...getPageMeta(NEW_SOFTWARE_SEO),
    ],
    links: [getCanonicalLink(NEW_SOFTWARE_SEO.path)],
  }),
})

function NewSoftwareRequestPage() {
  const navigate = useNavigate()
  const [submitError, setSubmitError] = useState<string>()

  // Fetch employee's assigned assets
  const assetsQuery = useAssets({ status: 'ASSIGNED' }, undefined, 100)
  const assignedAssets = assetsQuery.data?.items ?? []

  const assetOptions = useMemo<AutocompleteOption[]>(
    () =>
      assignedAssets.map((a) => ({
        value: a.asset_id,
        label: [a.brand, a.model].filter(Boolean).join(' ') || a.asset_id,
      })),
    [assignedAssets],
  )

  const assetSnMap = useMemo(
    () => new Map(assignedAssets.map((a) => [a.asset_id, a.serial_number])),
    [assignedAssets],
  )

  const [selectedAssetId, setSelectedAssetId] = useState('')
  const submitMutation = useSubmitSoftwareRequest(selectedAssetId)

  const form = useForm({
    defaultValues: {
      asset_id: '',
      software_name: '',
      version: '',
      vendor: '',
      justification: '',
      license_type: '',
      license_validity_period: '',
      data_access_impact: '' as DataAccessImpact | '',
    },
    validators: {
      onSubmit: softwareFormSchema,
    },
    onSubmit: async ({ value }) => {
      setSubmitError(undefined)
      try {
        await submitMutation.mutateAsync({
          software_name: value.software_name.trim(),
          version: value.version.trim(),
          vendor: value.vendor.trim(),
          justification: value.justification.trim(),
          license_type: value.license_type.trim(),
          license_validity_period: value.license_validity_period.trim(),
          data_access_impact: value.data_access_impact as DataAccessImpact,
        })
        toast.success(
          'Software request submitted. IT Admin will review your request.',
        )
        void navigate({ to: '/requests' })
      } catch (err) {
        if (err instanceof ApiError && err.status === 400) {
          setSubmitError(err.message)
        } else if (err instanceof ApiError) {
          toast.error(err.message)
        } else {
          toast.error('An unexpected error occurred. Please try again.')
        }
      }
    },
  })

  return (
    <main className="page-base">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link to="/requests">Requests</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>Software Request</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div className="my-4">
        <h1 className="text-2xl font-bold tracking-tight">
          Request Software Installation
        </h1>
        <p className="text-muted-foreground mt-1">
          Provide details about the software you need installed. IT Admin will
          review your request.
        </p>
      </div>

      <div>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            e.stopPropagation()
            void form.handleSubmit()
          }}
        >
          <FieldGroup>
            {/* Assigned Device */}
            <form.Field
              name="asset_id"
              children={(field) => {
                const isInvalid =
                  field.state.meta.isTouched && !field.state.meta.isValid
                return (
                  <Field data-invalid={isInvalid}>
                    <FieldLabel htmlFor={field.name}>
                      Assigned Device
                    </FieldLabel>
                    <Autocomplete
                      id={field.name}
                      value={field.state.value}
                      onChange={(v) => {
                        field.handleChange(v)
                        setSelectedAssetId(v)
                      }}
                      options={assetOptions}
                      context="device"
                      loading={assetsQuery.isLoading}
                      aria-invalid={isInvalid}
                      renderItem={(opt) => (
                        <div>
                          <p className="text-sm font-medium">{opt.label}</p>
                          {assetSnMap.get(opt.value) && (
                            <p className="text-xs text-muted-foreground">
                              SN: {assetSnMap.get(opt.value)}
                            </p>
                          )}
                        </div>
                      )}
                    />
                    {isInvalid && (
                      <FieldError errors={field.state.meta.errors} />
                    )}
                  </Field>
                )
              }}
            />

            {/* Software Name */}
            <form.Field
              name="software_name"
              children={(field) => {
                const isInvalid =
                  field.state.meta.isTouched && !field.state.meta.isValid
                return (
                  <Field data-invalid={isInvalid}>
                    <FieldLabel htmlFor={field.name}>Software Name</FieldLabel>
                    <Input
                      id={field.name}
                      name={field.name}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(e) => field.handleChange(e.target.value)}
                      aria-invalid={isInvalid}
                      placeholder="e.g. Visual Studio Code"
                    />
                    {isInvalid && (
                      <FieldError errors={field.state.meta.errors} />
                    )}
                  </Field>
                )
              }}
            />

            {/* Version */}
            <form.Field
              name="version"
              children={(field) => {
                const isInvalid =
                  field.state.meta.isTouched && !field.state.meta.isValid
                return (
                  <Field data-invalid={isInvalid}>
                    <FieldLabel htmlFor={field.name}>Version</FieldLabel>
                    <Input
                      id={field.name}
                      name={field.name}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(e) => field.handleChange(e.target.value)}
                      aria-invalid={isInvalid}
                      placeholder="e.g. 1.85.0"
                    />
                    {isInvalid && (
                      <FieldError errors={field.state.meta.errors} />
                    )}
                  </Field>
                )
              }}
            />

            {/* Vendor */}
            <form.Field
              name="vendor"
              children={(field) => {
                const isInvalid =
                  field.state.meta.isTouched && !field.state.meta.isValid
                return (
                  <Field data-invalid={isInvalid}>
                    <FieldLabel htmlFor={field.name}>Vendor</FieldLabel>
                    <Input
                      id={field.name}
                      name={field.name}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(e) => field.handleChange(e.target.value)}
                      aria-invalid={isInvalid}
                      placeholder="e.g. Microsoft"
                    />
                    {isInvalid && (
                      <FieldError errors={field.state.meta.errors} />
                    )}
                  </Field>
                )
              }}
            />

            {/* License Type */}
            <form.Field
              name="license_type"
              children={(field) => {
                const isInvalid =
                  field.state.meta.isTouched && !field.state.meta.isValid
                return (
                  <Field data-invalid={isInvalid}>
                    <FieldLabel htmlFor={field.name}>License Type</FieldLabel>
                    <Input
                      id={field.name}
                      name={field.name}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(e) => field.handleChange(e.target.value)}
                      aria-invalid={isInvalid}
                      placeholder="e.g. Perpetual, Subscription, Open Source"
                    />
                    {isInvalid && (
                      <FieldError errors={field.state.meta.errors} />
                    )}
                  </Field>
                )
              }}
            />

            {/* License Validity Period */}
            <form.Field
              name="license_validity_period"
              children={(field) => {
                const isInvalid =
                  field.state.meta.isTouched && !field.state.meta.isValid
                return (
                  <Field data-invalid={isInvalid}>
                    <FieldLabel htmlFor={field.name}>
                      License Validity Period
                    </FieldLabel>
                    <Input
                      id={field.name}
                      name={field.name}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(e) => field.handleChange(e.target.value)}
                      aria-invalid={isInvalid}
                      placeholder="e.g. 1 Year, Lifetime"
                    />
                    {isInvalid && (
                      <FieldError errors={field.state.meta.errors} />
                    )}
                  </Field>
                )
              }}
            />

            {/* Data Access Impact */}
            <form.Field
              name="data_access_impact"
              children={(field) => {
                const isInvalid =
                  field.state.meta.isTouched && !field.state.meta.isValid
                return (
                  <Field data-invalid={isInvalid}>
                    <FieldLabel htmlFor={field.name}>
                      Data Access Impact
                    </FieldLabel>
                    <Select
                      name={field.name}
                      value={field.state.value}
                      onValueChange={(v) =>
                        field.handleChange(v as DataAccessImpact)
                      }
                    >
                      <SelectTrigger id={field.name} aria-invalid={isInvalid}>
                        <SelectValue placeholder="Select impact level" />
                      </SelectTrigger>
                      <SelectContent>
                        {(
                          Object.entries(DataAccessImpactLabels) as [
                            DataAccessImpact,
                            string,
                          ][]
                        ).map(([value, label]) => (
                          <SelectItem key={value} value={value}>
                            {label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {isInvalid && (
                      <FieldError errors={field.state.meta.errors} />
                    )}
                  </Field>
                )
              }}
            />

            {/* Justification */}
            <form.Field
              name="justification"
              children={(field) => {
                const isInvalid =
                  field.state.meta.isTouched && !field.state.meta.isValid
                return (
                  <Field data-invalid={isInvalid}>
                    <FieldLabel htmlFor={field.name}>Justification</FieldLabel>
                    <Textarea
                      id={field.name}
                      name={field.name}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(e) => field.handleChange(e.target.value)}
                      aria-invalid={isInvalid}
                      placeholder="Explain why you need this software installed..."
                      rows={4}
                    />
                    {isInvalid && (
                      <FieldError errors={field.state.meta.errors} />
                    )}
                  </Field>
                )
              }}
            />
          </FieldGroup>

          {submitError && (
            <div className="alert-danger mt-4">{submitError}</div>
          )}

          <div className="flex items-center gap-3 mt-6">
            <Button
              type="submit"
              loading={submitMutation.isPending}
              className="flex-1"
            >
              Submit Request
            </Button>
            <Button type="button" variant="outline" asChild>
              <Link to="/requests">Cancel</Link>
            </Button>
          </div>
        </form>
      </div>
    </main>
  )
}
