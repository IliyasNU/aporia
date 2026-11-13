import { API_BASE, toApiError } from './client'

export type Health = {
  status: 'ok' | 'unavailable'
  database: 'ok' | 'unavailable'
}

/** GET /api/v1/health. A 503 still carries a Health body: the API runs, the database does not. */
export async function fetchHealth(signal?: AbortSignal): Promise<Health> {
  const response = await fetch(`${API_BASE}/health`, { signal })
  if (response.ok || response.status === 503) {
    return (await response.json()) as Health
  }
  throw await toApiError(response)
}
