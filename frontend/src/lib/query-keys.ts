import type {
  AssetStatus,
  ListSoftwareRequestsFilter,
  ListIssuesFilter,
  ListAllIssuesFilter,
  ListPendingReplacementsFilter,
  ListNotificationsFilter,
  ListReturnsFilter,
  ListAllReturnsFilter,
  ListDisposalsFilter,
  ListPendingDisposalsFilter,
} from './models/types'

export const queryKeys = {
  users: {
    all: () => ['users'] as const,
    list: (params: { cursor?: string; filters?: any }) =>
      [...queryKeys.users.all(), 'list', params] as const,
  },
  assets: {
    all: () => ['assets'] as const,
    list: (params: {
      cursor?: string
      status?: AssetStatus
      category?: string
      brand?: string
      model_name?: string
      date_from?: string
      date_to?: string
    }) => [...queryKeys.assets.all(), 'list', params] as const,
    detail: (assetId: string) =>
      [...queryKeys.assets.all(), 'detail', assetId] as const,
    scanJob: (scanJobId: string) =>
      [...queryKeys.assets.all(), 'scan-job', scanJobId] as const,
    handoverForm: (assetId: string) =>
      [...queryKeys.assets.all(), 'handover-form', assetId] as const,
    signatures: (
      employeeId: string,
      params: { cursor?: string; filters?: any },
    ) => [...queryKeys.assets.all(), 'signatures', employeeId, params] as const,
  },
  softwareRequests: {
    all: () => ['software-requests'] as const,
    list: (assetId: string, params: ListSoftwareRequestsFilter) =>
      [...queryKeys.softwareRequests.all(), 'list', assetId, params] as const,
    allRequests: (params: ListSoftwareRequestsFilter) =>
      [...queryKeys.softwareRequests.all(), 'all-requests', params] as const,
    detail: (assetId: string, softwareRequestId: string) =>
      [
        ...queryKeys.softwareRequests.all(),
        'detail',
        assetId,
        softwareRequestId,
      ] as const,
  },
  issues: {
    all: () => ['issues'] as const,
    list: (assetId: string, filters: ListIssuesFilter) =>
      [...queryKeys.issues.all(), 'list', assetId, filters] as const,
    allIssues: (filters: ListAllIssuesFilter) =>
      [...queryKeys.issues.all(), 'all-issues', filters] as const,
    detail: (assetId: string, issueId: string) =>
      [...queryKeys.issues.all(), 'detail', assetId, issueId] as const,
    pendingReplacements: (filters: ListPendingReplacementsFilter) =>
      [...queryKeys.issues.all(), 'pending-replacements', filters] as const,
  },
  returns: {
    all: () => ['returns'] as const,
    list: (assetId: string, filters: ListReturnsFilter) =>
      [...queryKeys.returns.all(), 'list', assetId, filters] as const,
    detail: (assetId: string, returnId: string) =>
      [...queryKeys.returns.all(), 'detail', assetId, returnId] as const,
    pendingSignatures: (filters: { cursor?: string }) =>
      [...queryKeys.returns.all(), 'pending-signatures', filters] as const,
    allReturns: (filters: ListAllReturnsFilter) =>
      [...queryKeys.returns.all(), 'all-returns', filters] as const,
  },
  notifications: {
    all: () => ['notifications'] as const,
    list: (filters: ListNotificationsFilter) =>
      [...queryKeys.notifications.all(), 'list', filters] as const,
    unreadCount: () =>
      [...queryKeys.notifications.all(), 'unread-count'] as const,
  },
  disposals: {
    all: () => ['disposals'] as const,
    list: (filters: ListDisposalsFilter) =>
      [...queryKeys.disposals.all(), 'list', filters] as const,
    detail: (assetId: string, disposalId: string) =>
      [...queryKeys.disposals.all(), 'detail', assetId, disposalId] as const,
    pendingDisposals: (filters: ListPendingDisposalsFilter) =>
      [...queryKeys.disposals.all(), 'pending', filters] as const,
  },
  auditLogs: {
    all: () => ['audit-logs'] as const,
    list: (assetId: string, params: { cursor?: string }) =>
      ['audit-logs', 'list', assetId, params] as const,
  },
  categories: {
    all: () => ['categories'] as const,
    list: (params: { cursor?: string }) =>
      [...queryKeys.categories.all(), 'list', params] as const,
  },
  dashboard: {
    all: () => ['dashboard'] as const,
    itAdminStats: () =>
      [...queryKeys.dashboard.all(), 'it-admin-stats'] as const,
    managementStats: () =>
      [...queryKeys.dashboard.all(), 'management-stats'] as const,
    employeeStats: () =>
      [...queryKeys.dashboard.all(), 'employee-stats'] as const,
    financeStats: () =>
      [...queryKeys.dashboard.all(), 'finance-stats'] as const,
    assetDistribution: () =>
      [...queryKeys.dashboard.all(), 'asset-distribution'] as const,
    recentActivity: () =>
      [...queryKeys.dashboard.all(), 'recent-activity'] as const,
    approvalHub: () => [...queryKeys.dashboard.all(), 'approval-hub'] as const,
  },
  pageStats: {
    all: () => ['page-stats'] as const,
    assets: () => [...queryKeys.pageStats.all(), 'assets'] as const,
    requestsItAdmin: () =>
      [...queryKeys.pageStats.all(), 'requests-it-admin'] as const,
    requestsEmployee: () =>
      [...queryKeys.pageStats.all(), 'requests-employee'] as const,
  },
} as const
