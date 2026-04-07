import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiError } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type {
  AssetStatus,
  ListAssetsResponse,
  GenerateUploadUrlsRequest,
  GenerateUploadUrlsResponse,
  GetScanResultsResponse,
  GetAssetResponse,
  CreateAssetRequest,
  CreateAssetResponse,
  ApproveAssetRequest,
  ApproveAssetResponse,
  AssignAssetRequest,
  AssignAssetResponse,
  CancelAssignmentResponse,
  GetHandoverFormResponse,
  GenerateSignatureUploadUrlResponse,
  AcceptHandoverRequest,
  AcceptHandoverResponse,
  ListEmployeeSignaturesResponse,
} from '#/lib/models/types'

export type AssetFilters = {
  status?: AssetStatus
  category?: string
  brand?: string
  model_name?: string
  date_from?: string
  date_to?: string
}

export function useAssets(
  filters: AssetFilters,
  cursor: string | undefined,
  pageSize: number = 10,
  enabled: boolean = true,
) {
  const queryParams: Record<string, string> = {}
  if (cursor) queryParams.cursor = cursor
  if (filters.status) queryParams.status = filters.status
  if (filters.category) queryParams.category = filters.category
  if (filters.brand) queryParams.brand = filters.brand
  if (filters.model_name) queryParams.model_name = filters.model_name
  if (filters.date_from) queryParams.date_from = filters.date_from
  if (filters.date_to) queryParams.date_to = filters.date_to

  const keyParams = {
    cursor,
    ...(filters.status && { status: filters.status }),
    ...(filters.category && { category: filters.category }),
    ...(filters.brand && { brand: filters.brand }),
    ...(filters.model_name && { model_name: filters.model_name }),
    ...(filters.date_from && { date_from: filters.date_from }),
    ...(filters.date_to && { date_to: filters.date_to }),
  }

  return useQuery({
    queryKey: queryKeys.assets.list(keyParams),
    queryFn: () =>
      apiClient<ListAssetsResponse>(
        `/assets?${new URLSearchParams(queryParams).toString()}`,
      ),
    staleTime: 60_000,
    enabled,
  })
}

export function useAssetDetail(assetId: string) {
  return useQuery({
    queryKey: queryKeys.assets.detail(assetId),
    queryFn: () => apiClient<GetAssetResponse>(`/assets/${assetId}`),
    staleTime: 5 * 60_000,
  })
}

export function useUploadAsset() {
  return useMutation({
    mutationFn: async ({
      invoiceFile,
      photoFiles,
    }: {
      invoiceFile: File
      photoFiles: File[]
    }) => {
      const filesManifest: GenerateUploadUrlsRequest['files'] = [
        {
          name: invoiceFile.name,
          content_type: invoiceFile.type,
          type: 'invoice',
        },
        ...photoFiles.map((f) => ({
          name: f.name,
          content_type: f.type,
          type: 'gadget_photo' as const,
        })),
      ]

      const uploadUrlsResponse = await apiClient<GenerateUploadUrlsResponse>(
        '/assets/uploads',
        {
          method: 'POST',
          body: JSON.stringify({ files: filesManifest }),
        },
      )

      const allFiles = [invoiceFile, ...photoFiles]
      for (let i = 0; i < uploadUrlsResponse.urls.length; i++) {
        const urlItem = uploadUrlsResponse.urls[i]
        const res = await fetch(urlItem.presigned_url, {
          method: 'PUT',
          body: allFiles[i],
          headers: { 'Content-Type': allFiles[i].type },
        })
        if (!res.ok) {
          throw new Error('One or more file uploads failed')
        }
      }

      return {
        upload_session_id: uploadUrlsResponse.upload_session_id,
        scan_job_id: uploadUrlsResponse.scan_job_id,
      }
    },
  })
}

export function useScanJob(scanJobId: string | null) {
  return useQuery({
    queryKey: queryKeys.assets.scanJob(scanJobId ?? ''),
    queryFn: () =>
      apiClient<GetScanResultsResponse>(`/assets/scan/${scanJobId}`),
    enabled: !!scanJobId,
    refetchInterval: (query) => {
      if (query.state.error) return false
      return query.state.data?.status === 'PROCESSING' ? 3000 : false
    },
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 422) return false
      return failureCount < 3
    },
  })
}

export function useCreateAsset() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['assets', 'create'],
    mutationFn: (data: CreateAssetRequest) =>
      apiClient<CreateAssetResponse>('/assets', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.assets.all() })
    },
  })
}

export function useApproveAsset(assetId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['assets', 'approve', assetId],
    mutationFn: (data: ApproveAssetRequest) =>
      apiClient<ApproveAssetResponse>(`/assets/${assetId}/approve`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.assets.all() })
    },
  })
}

export function useAssignAsset(assetId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['assets', 'assign', assetId],
    mutationFn: (data: AssignAssetRequest) =>
      apiClient<AssignAssetResponse>(`/assets/${assetId}/assign`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.assets.all() })
    },
  })
}

export function useCancelAssignment(assetId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['assets', 'cancel-assignment', assetId],
    mutationFn: () =>
      apiClient<CancelAssignmentResponse>(
        `/assets/${assetId}/cancel-assignment`,
        {
          method: 'DELETE',
        },
      ),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.assets.all() })
    },
  })
}

export function useAcceptHandover(assetId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['assets', 'accept', assetId],
    mutationFn: (data: AcceptHandoverRequest) =>
      apiClient<AcceptHandoverResponse>(`/assets/${assetId}/accept`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.assets.all() })
    },
  })
}

export function useHandoverForm(assetId: string) {
  return useMutation({
    mutationKey: ['assets', 'handover-form', assetId],
    mutationFn: () =>
      apiClient<GetHandoverFormResponse>(`/assets/${assetId}/assign-pdf-form`),
  })
}

export function useSignedHandoverForm(assetId: string) {
  return useMutation({
    mutationKey: ['assets', 'signed-handover-form', assetId],
    mutationFn: () =>
      apiClient<GetHandoverFormResponse>(`/assets/${assetId}/signed-pdf-form`),
  })
}

export function useSignatureUploadUrl(assetId: string) {
  return useMutation({
    mutationKey: ['assets', 'signature-upload-url', assetId],
    mutationFn: () =>
      apiClient<GenerateSignatureUploadUrlResponse>(
        `/assets/${assetId}/signature-upload-url`,
        {
          method: 'POST',
        },
      ),
  })
}

export function useEmployeeSignatures(
  employeeId: string,
  params: {
    cursor?: string
    filters?: {
      assignment_date_from?: string
      assignment_date_to?: string
    }
  },
) {
  const queryParams: Record<string, string> = {}
  if (params.cursor) queryParams.cursor = params.cursor
  if (params.filters?.assignment_date_from)
    queryParams.assignment_date_from = params.filters.assignment_date_from
  if (params.filters?.assignment_date_to)
    queryParams.assignment_date_to = params.filters.assignment_date_to

  return useQuery({
    queryKey: queryKeys.assets.signatures(employeeId, params),
    queryFn: () =>
      apiClient<ListEmployeeSignaturesResponse>(
        `/users/${employeeId}/signatures?${new URLSearchParams(queryParams).toString()}`,
      ),
    staleTime: 60_000,
  })
}
