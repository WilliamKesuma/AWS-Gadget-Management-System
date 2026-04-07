import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type {
  ListDisposalsFilter,
  ListDisposalsResponse,
  ListPendingDisposalsResponse,
  GetDisposalDetailsResponse,
  InitiateDisposalRequest,
  InitiateDisposalResponse,
  ManagementReviewDisposalRequest,
  ManagementReviewDisposalResponse,
  CompleteDisposalRequest,
  CompleteDisposalResponse,
} from '#/lib/models/types'

// ── Query Hooks ───────────────────────────────────────────────────────────────

export function useDisposalDetail(assetId: string, disposalId: string) {
  return useQuery({
    queryKey: queryKeys.disposals.detail(assetId, disposalId),
    queryFn: () =>
      apiClient<GetDisposalDetailsResponse>(
        `/assets/${assetId}/disposals/${disposalId}`,
      ),
    staleTime: 5 * 60_000,
  })
}

export function useDisposals(
  filters: ListDisposalsFilter,
  cursor: string | undefined,
  pageSize: number = 10,
) {
  const queryParams: Record<string, string> = {}
  if (cursor) queryParams.cursor = cursor
  if (filters.status) queryParams.status = filters.status
  if (filters.disposal_reason)
    queryParams.disposal_reason = filters.disposal_reason
  if (filters.date_from) queryParams.date_from = filters.date_from
  if (filters.date_to) queryParams.date_to = filters.date_to
  if (filters.history) queryParams.history = 'true'
  if (filters.asset_id) queryParams.asset_id = filters.asset_id

  const keyParams: ListDisposalsFilter = {
    cursor,
    ...(filters.status && { status: filters.status }),
    ...(filters.disposal_reason && {
      disposal_reason: filters.disposal_reason,
    }),
    ...(filters.date_from && { date_from: filters.date_from }),
    ...(filters.date_to && { date_to: filters.date_to }),
    ...(filters.history && { history: filters.history }),
    ...(filters.asset_id && { asset_id: filters.asset_id }),
  }

  return useQuery({
    queryKey: queryKeys.disposals.list(keyParams),
    queryFn: () =>
      apiClient<ListDisposalsResponse>(
        `/disposals?${new URLSearchParams(queryParams).toString()}`,
      ),
    staleTime: 60_000,
  })
}

export function usePendingDisposals(
  cursor: string | undefined,
  pageSize: number = 10,
  history: boolean = false,
) {
  const queryParams: Record<string, string> = {}
  if (cursor) queryParams.cursor = cursor
  if (history) queryParams.history = 'true'

  return useQuery({
    queryKey: queryKeys.disposals.pendingDisposals({
      cursor,
      history,
    }),
    queryFn: () =>
      apiClient<ListPendingDisposalsResponse>(
        `/disposals/pending?${new URLSearchParams(queryParams).toString()}`,
      ),
    staleTime: 60_000,
  })
}

// ── Mutation Hooks ────────────────────────────────────────────────────────────

export function useInitiateDisposal(assetId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['disposals', 'initiate', assetId],
    mutationFn: (data: InitiateDisposalRequest) =>
      apiClient<InitiateDisposalResponse>(`/assets/${assetId}/disposals`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.assets.detail(assetId),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.disposals.list({}),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.disposals.pendingDisposals({}),
      })
    },
  })
}

export function useManagementReviewDisposal(
  assetId: string,
  disposalId: string,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['disposals', 'management-review', assetId, disposalId],
    mutationFn: (data: ManagementReviewDisposalRequest) =>
      apiClient<ManagementReviewDisposalResponse>(
        `/assets/${assetId}/disposals/${disposalId}/management-review`,
        {
          method: 'PUT',
          body: JSON.stringify(data),
        },
      ),
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.disposals.detail(assetId, disposalId),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.disposals.list({}),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.disposals.pendingDisposals({}),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.assets.detail(assetId),
      })
    },
  })
}

export function useCompleteDisposal(assetId: string, disposalId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['disposals', 'complete', assetId, disposalId],
    mutationFn: (data: CompleteDisposalRequest) =>
      apiClient<CompleteDisposalResponse>(
        `/assets/${assetId}/disposals/${disposalId}/complete`,
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
        queryKey: queryKeys.assets.all(),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.disposals.detail(assetId, disposalId),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.disposals.list({}),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.disposals.pendingDisposals({}),
      })
    },
  })
}
