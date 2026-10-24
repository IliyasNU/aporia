import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { guest, makeArticle, makeMe, mockApi, renderApp } from '../test/api'

describe('ArticlePage', () => {
  it('renders the essay with its author, date and tags', async () => {
    mockApi({
      'GET /auth/me': guest,
      'GET /articles/on-doubt': { status: 200, body: makeArticle() },
    })

    renderApp('/articles/on-doubt')

    expect(await screen.findByRole('heading', { level: 1, name: 'On Doubt' })).toBeInTheDocument()
    expect(screen.getByText('I know that I know nothing.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Socrates' })).toHaveAttribute(
      'href',
      '/authors/socrates',
    )
    expect(screen.getByText('1 Mar 2026')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Epistemology' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Edit' })).toBeNull()
    expect(document.title).toBe('On Doubt · Aporia')
  })

  it('shows "not found" for missing, unpublished or other people\'s draft essays', async () => {
    mockApi({ 'GET /auth/me': guest })

    renderApp('/articles/secret-draft')

    expect(
      await screen.findByRole('heading', { name: 'This essay does not exist' }),
    ).toBeInTheDocument()
  })

  it('lets the author edit and marks drafts as private', async () => {
    mockApi({
      'GET /auth/me': { status: 200, body: makeMe({ id: 'author-1' }) },
      'GET /articles/on-doubt': {
        status: 200,
        body: makeArticle({ status: 'draft', published_at: null }),
      },
    })

    renderApp('/articles/on-doubt')

    expect(await screen.findByText('Draft: only you can see this essay.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Edit' })).toHaveAttribute('href', '/write/article-1')
  })
})
