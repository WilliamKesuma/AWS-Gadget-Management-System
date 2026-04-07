import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type {
  ListReturnsFilter,
  ListReturnsResponse,
  ListAllReturnsFilter,
  ListAllReturnsResponse,
  ListPendingSignaturesResponse,
  GetReturnResponse,
  InitiateReturnRequest,
  InitiateReturnResponse,
  GenerateReturnUploadUrlsRequest,
  GenerateReturnUploadUrlsResponse,
  GenerateReturnSignatureUploadUrlResponse,
  SubmitAdminReturnEvidenceResponse,
  CompleteReturnRequest,
  CompleteReturnResponse,
} from '#/lib/models/types'

// ── Query Hooks ───────────────────────────────────────────────────────────────

export function useReturnDetail(assetId: string, returnId: string) {
  return useQuery({
    queryKey: queryKeys.returns.detail(assetId, returnId),
    queryFn: () =>
      apiClient<GetReturnResponse>(`/assets/${assetId}/returns/${returnId}`),
    staleTime: 60_000,
  })
}

export function useReturns(
  assetId: string,
  filters: ListReturnsFilter,
  cursor: string | undefined,
  pageSize: number = 10,
) {
  const queryParams: Record<string, string> = {}
  if (cursor) queryParams.cursor = cursor
  if (filters.return_trigger)
    queryParams.return_trigger = filters.return_trigger
  if (filters.condition_assessment)
    queryParams.condition_assessment = filters.condition_assessment
  if (filters.history) queryParams.history = 'true'

  const keyFilters: ListReturnsFilter = {
    cursor,
    ...(filters.return_trigger && { return_trigger: filters.return_trigger }),
    ...(filters.condition_assessment && {
      condition_assessment: filters.condition_assessment,
    }),
    ...(filters.history && { history: filters.history }),
  }

  return useQuery({
    queryKey: queryKeys.returns.list(assetId, keyFilters),
    queryFn: () =>
      apiClient<ListReturnsResponse>(
        `/assets/${assetId}/returns?${new URLSearchParams(queryParams).toString()}`,
      ),
    staleTime: 60_000,
  })
}

export function useAllReturns(
  filters: ListAllReturnsFilter,
  cursor: string | undefined,
  pageSize: number = 10,
) {
  const queryParams: Record<string, string> = {}
  if (cursor) queryParams.cursor = cursor
  if (filters.status) queryParams.status = filters.status
  if (filters.return_trigger)
    queryParams.return_trigger = filters.return_trigger
  if (filters.condition_assessment)
    queryParams.condition_assessment = filters.condition_assessment
  if (filters.history) queryParams.history = 'true'
  if (filters.asset_id) queryParams.asset_id = filters.asset_id

  const keyParams: ListAllReturnsFilter = {
    cursor,
    ...(filters.status && { status: filters.status }),
    ...(filters.return_trigger && { return_trigger: filters.return_trigger }),
    ...(filters.condition_assessment && {
      condition_assessment: filters.condition_assessment,
    }),
    ...(filters.history && { history: filters.history }),
    ...(filters.asset_id && { asset_id: filters.asset_id }),
  }

  return useQuery({
    queryKey: queryKeys.returns.allReturns(keyParams),
    queryFn: () =>
      apiClient<ListAllReturnsResponse>(
        `/returns?${new URLSearchParams(queryParams).toString()}`,
      ),
    staleTime: 60_000,
  })
}

export function usePendingSignatures(
  cursor: string | undefined,
  pageSize: number = 10,
) {
  const queryParams: Record<string, string> = {}
  if (cursor) queryParams.cursor = cursor

  return useQuery({
    queryKey: queryKeys.returns.pendingSignatures({
      cursor,
    }),
    queryFn: () =>
      apiClient<ListPendingSignaturesResponse>(
        `/users/me/pending-signatures?${new URLSearchParams(queryParams).toString()}`,
      ),
    staleTime: 60_000,
  })
}

// ── Mutation Hooks ────────────────────────────────────────────────────────────

export function useInitiateReturn(assetId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['returns', 'initiate', assetId],
    mutationFn: (data: InitiateReturnRequest) =>
      apiClient<InitiateReturnResponse>(`/assets/${assetId}/returns`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.assets.detail(assetId),
      })
      void queryClient.invalidateQueries({ queryKey: queryKeys.assets.all() })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.returns.list(assetId, {}),
      })
    },
  })
}

export function useGenerateReturnUploadUrls(assetId: string) {
  return useMutation({
    mutationKey: ['returns', 'upload-urls', assetId],
    mutationFn: (
      data: GenerateReturnUploadUrlsRequest & { returnId: string },
    ) =>
      apiClient<GenerateReturnUploadUrlsResponse>(
        `/assets/${assetId}/returns/${data.returnId}/upload-urls`,
        {
          method: 'POST',
          body: JSON.stringify({ files: data.files }),
        },
      ),
  })
}

export function useSubmitAdminEvidence(assetId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['returns', 'submit-evidence', assetId],
    mutationFn: (returnId: string) =>
      apiClient<SubmitAdminReturnEvidenceResponse>(
        `/assets/${assetId}/returns/${returnId}/submit-evidence`,
        {
          method: 'POST',
          body: JSON.stringify({}),
        },
      ),
    onSettled: (_data, _err, returnId) => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.returns.detail(assetId, returnId),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.returns.list(assetId, {}),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.returns.pendingSignatures({}),
      })
    },
  })
}

export function useGenerateReturnSignatureUploadUrl(
  assetId: string,
  returnId: string,
) {
  return useMutation({
    mutationKey: ['returns', 'signature-upload-url', assetId, returnId],
    mutationFn: () =>
      apiClient<GenerateReturnSignatureUploadUrlResponse>(
        `/assets/${assetId}/returns/${returnId}/signature-upload-url`,
        {
          method: 'POST',
          body: JSON.stringify({ file_name: 'user-signature.png' }),
        },
      ),
  })
}

export function useCompleteReturn(assetId: string, returnId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['returns', 'complete', assetId, returnId],
    mutationFn: (data: CompleteReturnRequest) =>
      apiClient<CompleteReturnResponse>(
        `/assets/${assetId}/returns/${returnId}/complete`,
        {
          method: 'PUT',
          body: JSON.stringify(data),
        },
      ),
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.assets.detail(assetId),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.returns.detail(assetId, returnId),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.returns.list(assetId, {}),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.returns.pendingSignatures({}),
      })
    },
  })
}
