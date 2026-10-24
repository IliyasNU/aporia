import { api, ApiError } from './client'
import type { Me } from './types'

export type RegisterData = {
  email: string
  password: string
  handle: string
  display_name: string
}

export const register = (data: RegisterData) =>
  api<Me>('/auth/register', { method: 'POST', body: data })

export const login = (email: string, password: string) =>
  api<Me>('/auth/login', { method: 'POST', body: { email, password } })

export const logout = () => api<void>('/auth/logout', { method: 'POST' })

/** The signed-in user, or null for guests. */
export async function fetchMe(signal?: AbortSignal): Promise<Me | null> {
  try {
    return await api<Me>('/auth/me', { signal })
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null
    throw error
  }
}
