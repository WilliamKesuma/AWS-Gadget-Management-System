import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type {
  ListSoftwareRequestsFilter,
  ListSoftwareRequestsResponse,
  GetSoftwareRequestResponse,
  SubmitSoftwareRequestRequest,
  SubmitSoftwareRequestResponse,
  ReviewSoftwareRequestRequest,
  ReviewSoftwareRequestResponse,
  ManagementReviewSoftwareRequestRequest,
  ManagementReviewSoftwareRequestResponse,
} from '#/lib/models/types'

export function useSoftwareRequests(
  assetId: string,
  filters: ListSoftwareRequestsFilter,
  cursor: string | undefined,
  pageSize: number = 10,
) {
  const queryParams: Record<string, string> = {}
  if (cursor) queryParams.cursor = cursor
  if (filters.status) queryParams.status = filters.status
  if (filters.risk_level) queryParams.risk_level = filters.risk_level
  if (filters.software_name) queryParams.software_name = filters.software_name
  if (filters.vendor) queryParams.vendor = filters.vendor
  if (filters.license_validity_period)
    queryParams.license_validity_period = filters.license_validity_period
  if (filters.data_access_impact)
    queryParams.data_access_impact = filters.data_access_impact
  if (filters.history) queryParams.history = 'true'

  const keyParams: ListSoftwareRequestsFilter = {
    cursor,
    ...(filters.status && { status: filters.status }),
    ...(filters.risk_level && { risk_level: filters.risk_level }),
    ...(filters.software_name && { software_name: filters.software_name }),
    ...(filters.vendor && { vendor: filters.vendor }),
    ...(filters.license_validity_period && {
      license_validity_period: filters.license_validity_period,
    }),
    ...(filters.data_access_impact && {
      data_access_impact: filters.data_access_impact,
    }),
    ...(filters.history && { history: filters.history }),
  }

  return useQuery({
    queryKey: queryKeys.softwareRequests.list(assetId, keyParams),
    queryFn: () =>
      apiClient<ListSoftwareRequestsResponse>(
        `/assets/${assetId}/software-requests?${new URLSearchParams(queryParams).toString()}`,
      ),
    staleTime: 60_000,
  })
}

export function useSoftwareRequestDetail(
  assetId: string,
  softwareRequestId: string,
) {
  return useQuery({
    queryKey: queryKeys.softwareRequests.detail(assetId, softwareRequestId),
    queryFn: () =>
      apiClient<GetSoftwareRequestResponse>(
        `/assets/${assetId}/software-requests/${softwareRequestId}`,
      ),
    staleTime: 5 * 60_000,
  })
}

export function useAllSoftwareRequests(
  filters: ListSoftwareRequestsFilter,
  cursor: string | undefined,
  pageSize: number = 10,
) {
  const queryParams: Record<string, string> = {}
  if (cursor) queryParams.cursor = cursor
  if (filters.status) queryParams.status = filters.status
  if (filters.risk_level) queryParams.risk_level = filters.risk_level
  if (filters.software_name) queryParams.software_name = filters.software_name
  if (filters.vendor) queryParams.vendor = filters.vendor
  if (filters.license_validity_period)
    queryParams.license_validity_period = filters.license_validity_period
  if (filters.data_access_impact)
    queryParams.data_access_impact = filters.data_access_impact
  if (filters.history) queryParams.history = 'true'
  if (filters.asset_id) queryParams.asset_id = filters.asset_id

  const keyParams: ListSoftwareRequestsFilter = {
    cursor,
    ...(filters.status && { status: filters.status }),
    ...(filters.risk_level && { risk_level: filters.risk_level }),
    ...(filters.software_name && { software_name: filters.software_name }),
    ...(filters.vendor && { vendor: filters.vendor }),
    ...(filters.license_validity_period && {
      license_validity_period: filters.license_validity_period,
    }),
    ...(filters.data_access_impact && {
      data_access_impact: filters.data_access_impact,
    }),
    ...(filters.history && { history: filters.history }),
    ...(filters.asset_id && { asset_id: filters.asset_id }),
  }

  return useQuery({
    queryKey: queryKeys.softwareRequests.allRequests(keyParams),
    queryFn: () =>
      apiClient<ListSoftwareRequestsResponse>(
        `/software-requests?${new URLSearchParams(queryParams).toString()}`,
      ),
    staleTime: 60_000,
  })
}

export function useSubmitSoftwareRequest(assetId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['software-requests', 'submit', assetId],
    mutationFn: (data: SubmitSoftwareRequestRequest) =>
      apiClient<SubmitSoftwareRequestResponse>(
        `/assets/${assetId}/software-requests`,
        {
          method: 'POST',
          body: JSON.stringify(data),
        },
      ),
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.softwareRequests.list(assetId, {}),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.softwareRequests.allRequests({}),
      })
    },
  })
}

export function useReviewSoftwareRequest(
  assetId: string,
  softwareRequestId: string,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['software-requests', 'review', assetId, softwareRequestId],
    mutationFn: (data: ReviewSoftwareRequestRequest) =>
      apiClient<ReviewSoftwareRequestResponse>(
        `/assets/${assetId}/software-requests/${softwareRequestId}/review`,
        {
          method: 'PUT',
          body: JSON.stringify(data),
        },
      ),
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.softwareRequests.detail(assetId, softwareRequestId),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.softwareRequests.list(assetId, {}),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.softwareRequests.allRequests({}),
      })
    },
  })
}

export function useManagementReviewSoftwareRequest(
  assetId: string,
  softwareRequestId: string,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: [
      'software-requests',
      'management-review',
      assetId,
      softwareRequestId,
    ],
    mutationFn: (data: ManagementReviewSoftwareRequestRequest) =>
      apiClient<ManagementReviewSoftwareRequestResponse>(
        `/assets/${assetId}/software-requests/${softwareRequestId}/management-review`,
        {
          method: 'PUT',
          body: JSON.stringify(data),
        },
      ),
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.softwareRequests.detail(assetId, softwareRequestId),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.softwareRequests.allRequests({}),
      })
    },
  })
}
