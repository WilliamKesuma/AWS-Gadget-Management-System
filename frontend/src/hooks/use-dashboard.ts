import { useQuery } from '@tanstack/react-query'
import { apiClient } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type {
  ITAdminStatsResponse,
  ManagementStatsResponse,
  EmployeeStatsResponse,
  FinanceStatsResponse,
  AssetDistributionResponse,
  RecentActivityResponse,
  ApprovalHubResponse,
} from '#/lib/models/types'

const DASHBOARD_STALE_TIME = 5 * 60_000 // 5 minutes
const DASHBOARD_REFETCH_INTERVAL = 5 * 60_000 // 5 minutes

export function useITAdminStats() {
  return useQuery({
    queryKey: queryKeys.dashboard.itAdminStats(),
    queryFn: () => apiClient<ITAdminStatsResponse>('/dashboard/it-admin/stats'),
    staleTime: DASHBOARD_STALE_TIME,
    refetchInterval: DASHBOARD_REFETCH_INTERVAL,
  })
}

export function useManagementStats() {
  return useQuery({
    queryKey: queryKeys.dashboard.managementStats(),
    queryFn: () =>
      apiClient<ManagementStatsResponse>('/dashboard/management/stats'),
    staleTime: DASHBOARD_STALE_TIME,
    refetchInterval: DASHBOARD_REFETCH_INTERVAL,
  })
}

export function useEmployeeStats() {
  return useQuery({
    queryKey: queryKeys.dashboard.employeeStats(),
    queryFn: () =>
      apiClient<EmployeeStatsResponse>('/dashboard/employee/stats'),
    staleTime: DASHBOARD_STALE_TIME,
    refetchInterval: DASHBOARD_REFETCH_INTERVAL,
  })
}

export function useFinanceStats() {
  return useQuery({
    queryKey: queryKeys.dashboard.financeStats(),
    queryFn: () => apiClient<FinanceStatsResponse>('/dashboard/finance/stats'),
    staleTime: DASHBOARD_STALE_TIME,
    refetchInterval: DASHBOARD_REFETCH_INTERVAL,
  })
}

export function useAssetDistribution() {
  return useQuery({
    queryKey: queryKeys.dashboard.assetDistribution(),
    queryFn: () =>
      apiClient<AssetDistributionResponse>('/dashboard/asset-distribution'),
    staleTime: DASHBOARD_STALE_TIME,
    refetchInterval: DASHBOARD_REFETCH_INTERVAL,
  })
}

export function useRecentActivity() {
  return useQuery({
    queryKey: queryKeys.dashboard.recentActivity(),
    queryFn: () =>
      apiClient<RecentActivityResponse>('/dashboard/recent-activity'),
    staleTime: DASHBOARD_STALE_TIME,
    refetchInterval: DASHBOARD_REFETCH_INTERVAL,
  })
}

export function useApprovalHub() {
  return useQuery({
    queryKey: queryKeys.dashboard.approvalHub(),
    queryFn: () =>
      apiClient<ApprovalHubResponse>('/dashboard/management/approval-hub'),
    staleTime: DASHBOARD_STALE_TIME,
    refetchInterval: DASHBOARD_REFETCH_INTERVAL,
  })
}
