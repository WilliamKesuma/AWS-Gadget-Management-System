export type PaginatedAPIResponse<T> = {
  items: T[]
  count: number
  next_cursor: string | null
  has_next_page: boolean
}

export type PaginatedAPIFilter = {
  cursor?: string
  sort_order?: 'asc' | 'desc'
}
