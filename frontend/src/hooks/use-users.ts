import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useCallback } from 'react'
import { apiClient } from '#/lib/api-client'
import type { UserRole, UserStatus } from '#/lib/models/types'
import { queryKeys } from '#/lib/query-keys'
import { useDebounce } from '#/hooks/use-debounce'
import type {
  ListUsersResponse,
  CreateUserRequest,
  CreateUserResponse,
  DeactivateUserResponse,
} from '#/lib/models/types'

export function useUsers(pageSize: number = 10) {
  const queryClient = useQueryClient()

  const [currentCursor, setCurrentCursor] = useState<string | undefined>(undefined)
  const [cursorStack, setCursorStack] = useState<string[]>([])
  const [nameSearch, setNameSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<UserRole | 'all'>('all')
  const [statusFilter, setStatusFilter] = useState<UserStatus | 'all'>('all')

  const resetPagination = useCallback(() => {
    setCursorStack([])
    setCurrentCursor(undefined)
  }, [])

  const handleNameSearchChange = (value: string) => {
    setNameSearch(value)
    resetPagination()
  }

  const handleRoleFilterChange = (value: UserRole | 'all') => {
    setRoleFilter(value)
    resetPagination()
  }

  const handleStatusFilterChange = (value: UserStatus | 'all') => {
    setStatusFilter(value)
    resetPagination()
  }

  const debouncedName = useDebounce(nameSearch, 400)

  const effectiveParams = {
    cursor: currentCursor,
    filters: {
      name: debouncedName || undefined,
      role: roleFilter === 'all' ? undefined : roleFilter,
      status: statusFilter === 'all' ? undefined : statusFilter,
    },
  }

  const listQuery = useQuery({
    queryKey: queryKeys.users.list(effectiveParams),
    queryFn: async () => {
      const { cursor, filters } = effectiveParams
      const queryParams = new URLSearchParams({
        ...(cursor && { cursor }),
        ...(filters?.name && { name: filters.name }),
        ...(filters?.status && { status: filters.status }),
        ...(filters?.role && { role: filters.role }),
      })

      return apiClient<ListUsersResponse>(`/users?${queryParams.toString()}`)
    },
    staleTime: 60 * 1000,
  })

  const goToNextPage = useCallback((nextCursor: string) => {
    setCurrentCursor((prev) => {
      setCursorStack((stack) => [...stack, prev ?? ''])
      return nextCursor
    })
  }, [])

  const goToPreviousPage = useCallback(() => {
    setCursorStack((prev) => {
      const newStack = [...prev]
      const previousCursor = newStack.pop()
      setCurrentCursor(previousCursor || undefined)
      return newStack
    })
  }, [])

  const createUserMutation = useMutation({
    mutationFn: (data: CreateUserRequest) =>
      apiClient<CreateUserResponse>('/users/create', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.users.all() })
    },
  })

  const deactivateUserMutation = useMutation({
    mutationFn: (userId: string) =>
      apiClient<DeactivateUserResponse>(`/users/${userId}/deactivate`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.users.all() })
    },
  })

  const reactivateUserMutation = useMutation({
    mutationFn: (userId: string) =>
      apiClient<any>(`/users/${userId}/reactivate`, {
        method: 'PUT',
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.users.all() })
    },
  })

  return {
    ...listQuery,

    // Cursor pagination
    currentCursor,
    cursorStack,
    goToNextPage,
    goToPreviousPage,
    resetPagination,
    canGoPrevious: cursorStack.length > 0,
    hasNextPage: listQuery.data?.has_next_page ?? false,

    // State values exposed for UI components
    nameSearch,
    setNameSearch: handleNameSearchChange,
    roleFilter,
    setRoleFilter: handleRoleFilterChange,
    statusFilter,
    setStatusFilter: handleStatusFilterChange,
    pageSize,

    // Mutators
    createUser: createUserMutation,
    deactivateUser: deactivateUserMutation,
    reactivateUser: reactivateUserMutation,
  }
}
