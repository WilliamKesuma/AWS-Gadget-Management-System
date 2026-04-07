import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type {
  CreateAssetCategoryRequest,
  CreateAssetCategoryResponse,
  ListAssetCategoriesResponse,
} from '#/lib/models/types'

export function useCategories(
  params: { cursor?: string } = {},
) {
  const { cursor } = params
  const queryParams: Record<string, string> = {}
  if (cursor) queryParams.cursor = cursor

  return useQuery({
    queryKey: queryKeys.categories.list({ cursor }),
    queryFn: () =>
      apiClient<ListAssetCategoriesResponse>(
        `/categories?${new URLSearchParams(queryParams).toString()}`,
      ),
    staleTime: 60_000,
  })
}

export function useAllCategories() {
  return useQuery({
    queryKey: queryKeys.categories.list({}),
    queryFn: () =>
      apiClient<ListAssetCategoriesResponse>(
        `/categories`,
      ),
    staleTime: 5 * 60_000,
  })
}

export function useCreateCategory() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['categories', 'create'],
    mutationFn: (data: CreateAssetCategoryRequest) =>
      apiClient<CreateAssetCategoryResponse>('/categories', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.categories.all(),
      })
    },
  })
}

export function useDeleteCategory() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['categories', 'delete'],
    mutationFn: (categoryId: string) =>
      apiClient<void>(`/categories/${categoryId}`, { method: 'DELETE' }),
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.categories.all(),
      })
    },
  })
}

/** Derive a display label from a SCREAMING_SNAKE_CASE category name */
export function formatCategoryName(name: string): string {
  return name
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ')
}
