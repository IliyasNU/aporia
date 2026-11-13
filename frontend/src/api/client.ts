/** Every API error has this shape (see backend/app/core/errors.py). */
export type ApiErrorBody = {
  error: {
    code: string
    message: string
    details?: { loc: string[]; msg: string; type: string }[]
  }
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: ApiErrorBody['error']['details']

  constructor(status: number, body: ApiErrorBody['error']) {
    super(body.message)
    this.name = 'ApiError'
    this.status = status
    this.code = body.code
    this.details = body.details
  }

  /** Validation messages by field name, e.g. { email: 'value is not a valid email address' }. */
  fieldErrors(): Record<string, string> {
    const errors: Record<string, string> = {}
    for (const detail of this.details ?? []) {
      const field = detail.loc[detail.loc.length - 1]
      if (field && !(field in errors)) errors[field] = detail.msg
    }
    return errors
  }
}

export const API_BASE = '/api/v1'

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== 'object' || value === null || !('error' in value)) {
    return false
  }
  const error = (value as { error: unknown }).error
  return typeof error === 'object' && error !== null && 'code' in error && 'message' in error
}

async function toApiError(response: Response): Promise<ApiError> {
  const body: unknown = await response.json().catch(() => null)
  if (isApiErrorBody(body)) {
    return new ApiError(response.status, body.error)
  }
  return new ApiError(response.status, {
    code: 'unknown_error',
    message: `Request failed (${response.status})`,
  })
}

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  body?: unknown
  signal?: AbortSignal
}

/**
 * Calls the API on the same origin, so the session cookie is sent automatically.
 * Non-2xx responses throw an ApiError carrying the server's code and message.
 */
export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const hasBody = options.body !== undefined
  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? 'GET',
    headers: hasBody ? { 'Content-Type': 'application/json' } : undefined,
    body: hasBody ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  })
  if (!response.ok) {
    throw await toApiError(response)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

/** Turns any thrown value into a message that is safe to show. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  return 'Could not reach the server. Check your connection and try again.'
}
