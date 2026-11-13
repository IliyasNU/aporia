import { api } from './client'
import type { Article, ArticleDetail, ArticleListItem, Page } from './types'

export type ArticleSort = 'latest' | 'popular'

export type ArticleQuery = {
  q?: string
  tag?: string
  author?: string
  sort?: ArticleSort
  page?: number
  pageSize?: number
}

export type ArticleDraft = {
  title: string
  summary: string
  body_markdown: string
  tags: string[]
}

export function queryString(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') search.set(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

export const listArticles = (query: ArticleQuery, signal?: AbortSignal) =>
  api<Page<ArticleListItem>>(
    `/articles${queryString({
      q: query.q,
      tag: query.tag,
      author: query.author,
      sort: query.sort === 'popular' ? 'popular' : undefined,
      page: query.page,
      page_size: query.pageSize,
    })}`,
    { signal },
  )

export const getArticle = (slug: string, signal?: AbortSignal) =>
  api<ArticleDetail>(`/articles/${encodeURIComponent(slug)}`, { signal })

export const createArticle = (draft: ArticleDraft) =>
  api<Article>('/articles', { method: 'POST', body: draft })

export const updateArticle = (id: string, draft: ArticleDraft) =>
  api<Article>(`/articles/${id}`, { method: 'PATCH', body: draft })

export const publishArticle = (id: string) =>
  api<Article>(`/articles/${id}/publish`, { method: 'POST' })

export const unpublishArticle = (id: string) =>
  api<Article>(`/articles/${id}/unpublish`, { method: 'POST' })

export const deleteArticle = (id: string) => api<void>(`/articles/${id}`, { method: 'DELETE' })

export const listMyArticles = (page: number, signal?: AbortSignal) =>
  api<Page<ArticleListItem>>(`/me/articles${queryString({ page, page_size: 20 })}`, { signal })

export const getMyArticle = (id: string, signal?: AbortSignal) =>
  api<Article>(`/me/articles/${id}`, { signal })
