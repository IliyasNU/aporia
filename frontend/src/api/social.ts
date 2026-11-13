import { queryString } from './articles'
import { api } from './client'
import type { ArticleListItem, Comment, FollowedAuthor, Page } from './types'

export const follow = (authorId: string) =>
  api<void>(`/authors/${authorId}/follow`, { method: 'POST' })

export const unfollow = (authorId: string) =>
  api<void>(`/authors/${authorId}/follow`, { method: 'DELETE' })

export const listFollowing = (signal?: AbortSignal) =>
  api<FollowedAuthor[]>('/me/following', { signal })

export const followingFeed = (page: number, signal?: AbortSignal) =>
  api<Page<ArticleListItem>>(`/feed/following${queryString({ page, page_size: 10 })}`, {
    signal,
  })

export const bookmark = (articleId: string) =>
  api<void>(`/articles/${articleId}/bookmark`, { method: 'POST' })

export const unbookmark = (articleId: string) =>
  api<void>(`/articles/${articleId}/bookmark`, { method: 'DELETE' })

export const listBookmarks = (page: number, signal?: AbortSignal) =>
  api<Page<ArticleListItem>>(`/me/bookmarks${queryString({ page, page_size: 20 })}`, { signal })

export const listComments = (articleId: string, signal?: AbortSignal) =>
  api<Comment[]>(`/articles/${articleId}/comments`, { signal })

export const addComment = (articleId: string, text: string) =>
  api<Comment>(`/articles/${articleId}/comments`, { method: 'POST', body: { text } })

export const editComment = (commentId: string, text: string) =>
  api<Comment>(`/comments/${commentId}`, { method: 'PATCH', body: { text } })

export const deleteComment = (commentId: string) =>
  api<void>(`/comments/${commentId}`, { method: 'DELETE' })

export type ReportTarget = 'article' | 'comment'

export const report = (targetType: ReportTarget, targetId: string, reason: string) =>
  api<void>('/reports', {
    method: 'POST',
    body: { target_type: targetType, target_id: targetId, reason },
  })
