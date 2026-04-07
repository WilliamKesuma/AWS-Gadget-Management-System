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
import { IssueCategorySchema, type IssueCategory } from '#/lib/models/types'
import { useAssets } from '#/hooks/use-assets'
import { useSubmitIssue } from '#/hooks/use-issues'
import { apiClient, ApiError } from '#/lib/api-client'
import type { GenerateIssueUploadUrlsResponse } from '#/lib/models/types'
import { Button } from '#/components/ui/button'
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
import { DragDropZone } from '#/components/assets/DragDropZone'
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
import { Monitor, AppWindow } from 'lucide-react'
import { cn } from '#/lib/utils'
import { hasRole } from '#/lib/permissions'

const NEW_ISSUE_SEO = {
  title: 'Report Issue',
  description:
    'Submit an issue report for your assigned gadget so the IT team can review and resolve it promptly.',
  path: '/requests/new-issue',
} satisfies SeoPageInput

const issueFormSchema = z.object({
  asset_id: z.string().min(1, 'Please select an assigned device.'),
  category: IssueCategorySchema,
  issue_description: z
    .string()
    .min(1, 'Issue description is required.')
    .refine(
      (v) => v.trim().length > 0,
      'Issue description cannot be whitespace only.',
    ),
})

export const Route = createFileRoute('/_authenticated/requests/new-issue')({
  beforeLoad: ({ context }) => {
    if (!hasRole(context.userRole, ['employee'])) {
      throw redirect({ to: '/unauthorized' })
    }
  },
  component: NewIssuePage,
  head: () => ({
    meta: [
      ...getBaseMeta(),
      { name: 'robots', content: 'noindex, nofollow' },
      ...getPageMeta(NEW_ISSUE_SEO),
    ],
    links: [getCanonicalLink(NEW_ISSUE_SEO.path)],
  }),
})

function NewIssuePage() {
  const navigate = useNavigate()
  const [files, setFiles] = useState<File[]>([])
  const [submitError, setSubmitError] = useState<string>()

  // Fetch employee's assigned assets for the dropdown
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

  // Track selected asset for the mutation hook
  const [selectedAssetId, setSelectedAssetId] = useState('')
  const submitMutation = useSubmitIssue(selectedAssetId)

  const form = useForm({
    defaultValues: {
      asset_id: '',
      category: '',
      issue_description: '',
    },
    validators: {
      onSubmit: issueFormSchema,
    },
    onSubmit: async ({ value }) => {
      setSubmitError(undefined)
      try {
        const response = await submitMutation.mutateAsync({
          issue_description: value.issue_description.trim(),
          category: value.category as IssueCategory,
        })

        // Upload photos if attached
        if (files.length > 0) {
          try {
            const manifest = files.map((f) => ({
              name: f.name,
              type: 'photo' as const,
              content_type: f.type,
            }))
            const uploadRes = await apiClient<GenerateIssueUploadUrlsResponse>(
              `/assets/${value.asset_id}/issues/${response.issue_id}/upload-urls`,
              { method: 'POST', body: JSON.stringify({ files: manifest }) },
            )
            await Promise.all(
              uploadRes.upload_urls.map((urlItem, idx) =>
                fetch(urlItem.presigned_url, {
                  method: 'PUT',
                  body: files[idx],
                  headers: { 'Content-Type': urlItem.content_type },
                }),
              ),
            )
          } catch {
            toast.error(
              'Issue reported but photo upload failed. You can upload photos later.',
            )
          }
        }

        toast.success(
          'Issue reported successfully. IT Admin has been notified.',
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
      {/* Breadcrumb */}
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link to="/requests">Requests</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>Report Issue</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      {/* Header */}
      <div className="my-4">
        <h1 className="text-2xl font-bold tracking-tight">
          Submit Issue Report
        </h1>
        <p className="text-muted-foreground mt-1">
          Provide details about the problem with your assigned gadget. Our IT
          team will review it shortly.
        </p>
      </div>

      {/* Form card */}
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

            {/* Issue Category */}
            <form.Field
              name="category"
              children={(field) => {
                const isInvalid =
                  field.state.meta.isTouched && !field.state.meta.isValid
                return (
                  <Field data-invalid={isInvalid}>
                    <FieldLabel>Issue Category</FieldLabel>
                    <div className="grid grid-cols-2 gap-3">
                      <button
                        type="button"
                        onClick={() => field.handleChange('HARDWARE')}
                        className={cn(
                          'flex items-center justify-center gap-2 rounded-lg border-2 px-4 py-3 text-sm font-medium transition-colors',
                          field.state.value === 'HARDWARE'
                            ? 'border-primary bg-primary/5 text-primary'
                            : 'border-border text-muted-foreground hover:border-primary/40',
                        )}
                      >
                        <Monitor className="size-4" />
                        Hardware
                      </button>
                      <button
                        type="button"
                        onClick={() => field.handleChange('SOFTWARE')}
                        className={cn(
                          'flex items-center justify-center gap-2 rounded-lg border-2 px-4 py-3 text-sm font-medium transition-colors',
                          field.state.value === 'SOFTWARE'
                            ? 'border-primary bg-primary/5 text-primary'
                            : 'border-border text-muted-foreground hover:border-primary/40',
                        )}
                      >
                        <AppWindow className="size-4" />
                        Software
                      </button>
                    </div>
                    {isInvalid && (
                      <FieldError errors={field.state.meta.errors} />
                    )}
                  </Field>
                )
              }}
            />

            {/* Description */}
            <form.Field
              name="issue_description"
              children={(field) => {
                const isInvalid =
                  field.state.meta.isTouched && !field.state.meta.isValid
                return (
                  <Field data-invalid={isInvalid}>
                    <FieldLabel htmlFor={field.name}>
                      Description of Issue
                    </FieldLabel>
                    <Textarea
                      id={field.name}
                      name={field.name}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(e) => field.handleChange(e.target.value)}
                      aria-invalid={isInvalid}
                      placeholder="Describe what happened, any error codes, or physical damage..."
                      rows={5}
                    />
                    {isInvalid && (
                      <FieldError errors={field.state.meta.errors} />
                    )}
                  </Field>
                )
              }}
            />

            {/* Attachments */}
            <Field>
              <FieldLabel>Attachments</FieldLabel>
              <DragDropZone
                accept="image/jpeg,image/png,application/pdf"
                maxFiles={5}
                label="Click to upload or drag and drop — PNG, JPG or PDF (max. 10MB)"
                files={files}
                onFilesChange={setFiles}
              />
            </Field>
          </FieldGroup>

          {submitError && (
            <div className="alert-danger mt-4">{submitError}</div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-3 mt-6">
            <Button
              type="submit"
              loading={submitMutation.isPending}
              className="flex-1"
            >
              Submit Report
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
