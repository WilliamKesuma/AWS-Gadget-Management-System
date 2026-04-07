import { useQuery } from '@tanstack/react-query'
import { apiClient } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { ListAuditLogsResponse } from '#/lib/models/types'

export function useAssetLogs(
    assetId: string,
    cursor: string | undefined,
    pageSize: number = 10,
) {
    const queryParams: Record<string, string> = {}
    if (cursor) queryParams.cursor = cursor

    return useQuery({
        queryKey: queryKeys.auditLogs.list(assetId, {
            cursor,
        }),
        queryFn: () =>
            apiClient<ListAuditLogsResponse>(
                `/assets/${assetId}/logs?${new URLSearchParams(queryParams).toString()}`,
            ),
        staleTime: 60_000,
    })
}
