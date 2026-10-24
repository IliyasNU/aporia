/** Every API error has this shape (see backend/app/core/errors.py). */
export type ApiErrorBody = {
  error: {
    code: string
    message: string
  }
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
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

/** Turns a non-2xx response into an ApiError with the server's code and message. */
export async function toApiError(response: Response): Promise<ApiError> {
  const body: unknown = await response.json().catch(() => null)
  if (isApiErrorBody(body)) {
    return new ApiError(response.status, body.error.code, body.error.message)
  }
  return new ApiError(response.status, 'unknown_error', `Request failed (${response.status})`)
}
