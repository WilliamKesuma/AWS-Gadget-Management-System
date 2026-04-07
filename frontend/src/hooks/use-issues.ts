import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type {
  ListIssuesFilter,
  ListIssuesResponse,
  ListAllIssuesFilter,
  ListAllIssuesResponse,
  GetIssueResponse,
  ListPendingReplacementsResponse,
  SubmitIssueRequest,
  SubmitIssueResponse,
  ResolveRepairRequest,
  ResolveRepairResponse,
  SendWarrantyRequest,
  SendWarrantyResponse,
  CompleteRepairRequest,
  CompleteRepairResponse,
  RequestReplacementRequest,
  RequestReplacementResponse,
  ManagementReviewIssueRequest,
  ManagementReviewIssueResponse,
} from '#/lib/models/types'

// ── Upload URL types (not in types.ts, defined inline) ────────────────────────

type IssueFileManifestItem = {
  name: string
  type: 'photo'
  content_type: string
}

type GenerateIssueUploadUrlsRequest = {
  files: IssueFileManifestItem[]
}

type IssuePresignedUrlItem = {
  file_key: string
  presigned_url: string
  type: string
  content_type: string
}

type GenerateIssueUploadUrlsResponse = {
  upload_urls: IssuePresignedUrlItem[]
}

// ── Query Hooks ───────────────────────────────────────────────────────────────

export function useIssues(
  assetId: string,
  filters: ListIssuesFilter,
  cursor: string | undefined,
  pageSize: number = 10,
) {
  const queryParams: Record<string, string> = {}
  if (cursor) queryParams.cursor = cursor
  if (filters.status) queryParams.status = filters.status
  if (filters.history) queryParams.history = 'true'

  const keyParams: ListIssuesFilter = {
    cursor,
    ...(filters.status && { status: filters.status }),
    ...(filters.history && { history: filters.history }),
  }

  return useQuery({
    queryKey: queryKeys.issues.list(assetId, keyParams),
    queryFn: () =>
      apiClient<ListIssuesResponse>(
        `/assets/${assetId}/issues?${new URLSearchParams(queryParams).toString()}`,
      ),
    staleTime: 60_000,
  })
}

export function useAllIssues(
  filters: ListAllIssuesFilter,
  cursor: string | undefined,
  pageSize: number = 10,
) {
  const queryParams: Record<string, string> = {}
  if (cursor) queryParams.cursor = cursor
  if (filters.status) queryParams.status = filters.status
  if (filters.category) queryParams.category = filters.category
  if (filters.sort_order) queryParams.sort_order = filters.sort_order
  if (filters.history) queryParams.history = 'true'
  if (filters.asset_id) queryParams.asset_id = filters.asset_id

  const keyParams: ListAllIssuesFilter = {
    cursor,
    ...(filters.status && { status: filters.status }),
    ...(filters.category && { category: filters.category }),
    ...(filters.sort_order && { sort_order: filters.sort_order }),
    ...(filters.history && { history: filters.history }),
    ...(filters.asset_id && { asset_id: filters.asset_id }),
  }

  return useQuery({
    queryKey: queryKeys.issues.allIssues(keyParams),
    queryFn: () =>
      apiClient<ListAllIssuesResponse>(
        `/issues?${new URLSearchParams(queryParams).toString()}`,
      ),
    staleTime: 60_000,
  })
}

export function useIssueDetail(assetId: string, issueId: string) {
  return useQuery({
    queryKey: queryKeys.issues.detail(assetId, issueId),
    queryFn: () =>
      apiClient<GetIssueResponse>(`/assets/${assetId}/issues/${issueId}`),
    staleTime: 5 * 60_000,
  })
}

export function usePendingReplacements(
  cursor: string | undefined,
  pageSize: number = 10,
  history: boolean = false,
) {
  const queryParams: Record<string, string> = {}
  if (cursor) queryParams.cursor = cursor
  if (history) queryParams.history = 'true'

  return useQuery({
    queryKey: queryKeys.issues.pendingReplacements({
      cursor,
      history,
    }),
    queryFn: () =>
      apiClient<ListPendingReplacementsResponse>(
        `/issues/pending-replacements?${new URLSearchParams(queryParams).toString()}`,
      ),
    staleTime: 60_000,
  })
}

// ── Mutation Hooks ────────────────────────────────────────────────────────────

export function useSubmitIssue(assetId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['issues', 'submit', assetId],
    mutationFn: (data: SubmitIssueRequest) =>
      apiClient<SubmitIssueResponse>(`/assets/${assetId}/issues`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.issues.list(assetId, {}),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.issues.allIssues({}),
      })
    },
  })
}

export function useGenerateIssueUploadUrls(assetId: string, issueId: string) {
  return useMutation({
    mutationKey: ['issues', 'upload-urls', assetId, issueId],
    mutationFn: (data: GenerateIssueUploadUrlsRequest) =>
      apiClient<GenerateIssueUploadUrlsResponse>(
        `/assets/${assetId}/issues/${issueId}/upload-urls`,
        {
          method: 'POST',
          body: JSON.stringify(data),
        },
      ),
  })
}

export function useResolveRepair(assetId: string, issueId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['issues', 'resolve-repair', assetId, issueId],
    mutationFn: (data: ResolveRepairRequest) =>
      apiClient<ResolveRepairResponse>(
        `/assets/${assetId}/issues/${issueId}/resolve-repair`,
        {
          method: 'PUT',
          body: JSON.stringify(data),
        },
      ),
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.issues.detail(assetId, issueId),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.issues.list(assetId, {}),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.issues.allIssues({}),
      })
    },
  })
}

export function useSendWarranty(assetId: string, issueId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['issues', 'send-warranty', assetId, issueId],
    mutationFn: (data: SendWarrantyRequest) =>
      apiClient<SendWarrantyResponse>(
        `/assets/${assetId}/issues/${issueId}/send-warranty`,
        {
          method: 'PUT',
          body: JSON.stringify(data),
        },
      ),
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.issues.detail(assetId, issueId),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.issues.list(assetId, {}),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.issues.allIssues({}),
      })
    },
  })
}

export function useCompleteRepair(assetId: string, issueId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['issues', 'complete-repair', assetId, issueId],
    mutationFn: (data: CompleteRepairRequest) =>
      apiClient<CompleteRepairResponse>(
        `/assets/${assetId}/issues/${issueId}/complete-repair`,
        {
          method: 'PUT',
          body: JSON.stringify(data),
        },
      ),
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.issues.detail(assetId, issueId),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.issues.list(assetId, {}),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.issues.allIssues({}),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.assets.detail(assetId),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.assets.all(),
      })
    },
  })
}

export function useRequestReplacement(assetId: string, issueId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['issues', 'request-replacement', assetId, issueId],
    mutationFn: (data: RequestReplacementRequest) =>
      apiClient<RequestReplacementResponse>(
        `/assets/${assetId}/issues/${issueId}/request-replacement`,
        {
          method: 'PUT',
          body: JSON.stringify(data),
        },
      ),
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.issues.detail(assetId, issueId),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.issues.list(assetId, {}),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.issues.allIssues({}),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.issues.pendingReplacements({}),
      })
    },
  })
}

export function useManagementReviewIssue(assetId: string, issueId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['issues', 'management-review', assetId, issueId],
    mutationFn: (data: ManagementReviewIssueRequest) =>
      apiClient<ManagementReviewIssueResponse>(
        `/assets/${assetId}/issues/${issueId}/management-review`,
        {
          method: 'PUT',
          body: JSON.stringify(data),
        },
      ),
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.issues.detail(assetId, issueId),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.issues.pendingReplacements({}),
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.issues.allIssues({}),
      })
    },
  })
}
