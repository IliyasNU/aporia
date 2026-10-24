import { api } from './client'
import type { AuthorBrief } from './types'

export const subscribeToAuthor = (authorId: string, email: string) =>
  api<{ message: string }>(`/authors/${authorId}/newsletter-subscriptions`, {
    method: 'POST',
    body: { email },
  })

export const confirmSubscription = (token: string) =>
  api<{ author: AuthorBrief }>('/newsletter/confirm', { method: 'POST', body: { token } })

export const unsubscribe = (token: string) =>
  api<void>('/newsletter/unsubscribe', { method: 'POST', body: { token } })

/**
 * Email links carry the token after "#token=". The part after # never reaches
 * any server, so tokens do not end up in access logs.
 */
export function tokenFromHash(hash: string): string | null {
  return new URLSearchParams(hash.replace(/^#/, '')).get('token')
}
