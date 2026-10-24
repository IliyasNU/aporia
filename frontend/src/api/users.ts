import { api } from './client'
import type { Author, Me, Tag, TagWithCount } from './types'

export type ProfileChanges = {
  display_name?: string
  bio?: string
  website?: string | null
}

export const getAuthor = (handle: string, signal?: AbortSignal) =>
  api<Author>(`/authors/${encodeURIComponent(handle)}`, { signal })

export const updateProfile = (changes: ProfileChanges) =>
  api<Me>('/me/profile', { method: 'PATCH', body: changes })

export const setInterests = (tags: string[]) =>
  api<{ interests: Tag[] }>('/me/interests', { method: 'PUT', body: { tags } })

export const listTags = (signal?: AbortSignal) => api<TagWithCount[]>('/tags', { signal })
