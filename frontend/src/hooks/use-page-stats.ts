import { useQuery } from '@tanstack/react-query'
import { apiClient } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type {
  AssetsPageStatsResponse,
  RequestsITAdminStatsResponse,
  RequestsEmployeeStatsResponse,
} from '#/lib/models/types'

export function useAssetsPageStats() {
  return useQuery({
    queryKey: queryKeys.pageStats.assets(),
    queryFn: () => apiClient<AssetsPageStatsResponse>('/pages/assets/stats'),
    staleTime: 60_000,
  })
}

export function useRequestsITAdminStats() {
  return useQuery({
    queryKey: queryKeys.pageStats.requestsItAdmin(),
    queryFn: () =>
      apiClient<RequestsITAdminStatsResponse>('/pages/requests/it-admin/stats'),
    staleTime: 60_000,
  })
}

export function useRequestsEmployeeStats() {
  return useQuery({
    queryKey: queryKeys.pageStats.requestsEmployee(),
    queryFn: () =>
      apiClient<RequestsEmployeeStatsResponse>(
        '/pages/requests/employee/stats',
      ),
    staleTime: 60_000,
  })
}
