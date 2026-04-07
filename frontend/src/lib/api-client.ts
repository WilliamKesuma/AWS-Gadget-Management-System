import { fetchAuthSession } from 'aws-amplify/auth'

export class ApiError extends Error {
  public failureReason?: string

  constructor(
    public status: number,
    public message: string,
    failureReason?: string,
  ) {
    super(message)
    this.name = 'ApiError'
    this.failureReason = failureReason
  }
}

const API_URL = import.meta.env.VITE_API_URL

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const session = await fetchAuthSession()
  const token = session.tokens?.idToken?.toString()

  const headers = new Headers(options.headers)
  if (token) {
    headers.set('Authorization', `${token}`)
  }
  headers.set('Content-Type', 'application/json')

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new ApiError(
      response.status,
      errorData.message || `API error: ${response.status}`,
      errorData.failure_reason,
    )
  }

  return response.json() as Promise<T>
}
