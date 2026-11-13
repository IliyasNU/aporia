import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { vi } from 'vitest'

import type { ArticleDetail, ArticleListItem, Comment, Me, Page, TagWithCount } from '../api/types'
import App from '../App'

export type Reply = { status: number; body?: unknown }
type Route = Reply | ((body: unknown) => Reply)
export type Call = { method: string; path: string; body: unknown }

/**
 * Replaces fetch with a fake API. Keys are "METHOD /path" (with or without the
 * query string, the exact one wins). Unknown routes answer 404.
 */
export function mockApi(routes: Record<string, Route>): Call[] {
  const calls: Call[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), 'http://localhost')
      const path = url.pathname.replace('/api/v1', '')
      const method = init?.method ?? 'GET'
      const body: unknown = init?.body ? JSON.parse(String(init.body)) : undefined
      calls.push({ method, path: path + url.search, body })
      const route = routes[`${method} ${path}${url.search}`] ?? routes[`${method} ${path}`]
      const reply: Reply =
        typeof route === 'function'
          ? route(body)
          : (route ?? { status: 404, body: { error: { code: 'not_found', message: 'Not Found' } } })
      return new Response(reply.status === 204 ? null : JSON.stringify(reply.body ?? {}), {
        status: reply.status,
        headers: { 'Content-Type': 'application/json' },
      })
    }),
  )
  return calls
}

export const guest: Reply = {
  status: 401,
  body: { error: { code: 'not_authenticated', message: 'Sign in to continue' } },
}

export function renderApp(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

export function makeMe(overrides: Partial<Me> = {}): Me {
  return {
    id: 'user-1',
    handle: 'ada',
    display_name: 'Ada Lovelace',
    bio: '',
    website: null,
    created_at: '2026-01-01T00:00:00Z',
    email: 'ada@example.com',
    role: 'user',
    interests: [],
    ...overrides,
  }
}

export function makeArticle(overrides: Partial<ArticleDetail> = {}): ArticleDetail {
  return {
    id: 'article-1',
    slug: 'on-doubt',
    title: 'On Doubt',
    summary: 'Why certainty is overrated.',
    status: 'published',
    author: { id: 'author-1', handle: 'socrates', display_name: 'Socrates' },
    tags: [{ slug: 'epistemology', name: 'Epistemology' }],
    published_at: '2026-03-01T10:00:00Z',
    updated_at: '2026-03-01T10:00:00Z',
    created_at: '2026-03-01T09:00:00Z',
    body_markdown: 'I know that I know nothing.',
    moderation_status: 'visible',
    bookmarked_by_me: false,
    following_author: false,
    ...overrides,
  }
}

export function page<T extends ArticleListItem>(items: T[], total = items.length): Page<T> {
  return { items, page: 1, page_size: 10, total }
}

export const tagCatalog: TagWithCount[] = [
  { slug: 'epistemology', name: 'Epistemology', article_count: 3 },
  { slug: 'ethics', name: 'Ethics', article_count: 0 },
  { slug: 'logic', name: 'Logic', article_count: 5 },
]

export function makeComment(overrides: Partial<Comment> = {}): Comment {
  return {
    id: 'comment-1',
    article_id: 'article-1',
    author: { id: 'user-2', handle: 'plato', display_name: 'Plato' },
    text: 'Well argued.',
    created_at: '2026-03-02T10:00:00Z',
    updated_at: '2026-03-02T10:00:00Z',
    ...overrides,
  }
}
