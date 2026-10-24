import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { guest, makeArticle, mockApi, page, renderApp, tagCatalog } from '../test/api'

describe('HomePage', () => {
  it('shows a loading state, then article cards and popular tags', async () => {
    mockApi({
      'GET /auth/me': guest,
      'GET /articles': { status: 200, body: page([makeArticle()]) },
      'GET /tags': { status: 200, body: tagCatalog },
    })

    renderApp('/')

    expect(screen.getByRole('status')).toHaveTextContent('Loading essays')
    expect(await screen.findByRole('link', { name: 'On Doubt' })).toHaveAttribute(
      'href',
      '/articles/on-doubt',
    )
    expect(screen.getByText('Why certainty is overrated.')).toBeInTheDocument()
    // Popular tags: only tags with articles, most used first.
    const tags = await screen.findAllByRole('button', { pressed: false })
    expect(tags.map((t) => t.textContent)).toEqual(['Logic 5', 'Epistemology 3'])
  })

  it('shows an empty state when nothing is published', async () => {
    mockApi({
      'GET /auth/me': guest,
      'GET /articles': { status: 200, body: page([]) },
      'GET /tags': { status: 200, body: tagCatalog },
    })

    renderApp('/')

    expect(await screen.findByText('No essays have been published yet.')).toBeInTheDocument()
  })

  it('shows an error with a working retry', async () => {
    let attempts = 0
    mockApi({
      'GET /auth/me': guest,
      'GET /articles': () =>
        ++attempts === 1
          ? {
              status: 500,
              body: { error: { code: 'internal_error', message: 'Internal server error' } },
            }
          : { status: 200, body: page([makeArticle()]) },
      'GET /tags': { status: 200, body: tagCatalog },
    })

    renderApp('/')

    expect(await screen.findByRole('alert')).toHaveTextContent('Internal server error')
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('link', { name: 'On Doubt' })).toBeInTheDocument()
  })

  it('searches, filters by tag and pages through the API', async () => {
    const calls = mockApi({
      'GET /auth/me': guest,
      'GET /articles': { status: 200, body: page([makeArticle()], 25) },
      'GET /tags': { status: 200, body: tagCatalog },
    })
    renderApp('/')
    await screen.findByRole('link', { name: 'On Doubt' })

    await userEvent.type(screen.getByRole('searchbox', { name: 'Search essays' }), 'doubt')
    await userEvent.click(screen.getByRole('button', { name: 'Search' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Logic 5' }))
    const pagination = await screen.findByRole('navigation', { name: 'Pagination' })
    await userEvent.click(within(pagination).getByRole('button', { name: 'Older →' }))

    const articleRequests = calls.filter((c) => c.path.startsWith('/articles')).map((c) => c.path)
    expect(articleRequests).toContain('/articles?q=doubt&page=1&page_size=10')
    expect(articleRequests).toContain('/articles?q=doubt&tag=logic&page=1&page_size=10')
    expect(articleRequests).toContain('/articles?q=doubt&tag=logic&page=2&page_size=10')
  })

  it('sends guests who want to write to the sign-in page', async () => {
    mockApi({
      'GET /auth/me': guest,
      'GET /articles': { status: 200, body: page([]) },
      'GET /tags': { status: 200, body: [] },
    })

    renderApp('/')

    expect(await screen.findByRole('link', { name: 'Write an essay' })).toHaveAttribute(
      'href',
      '/signin?next=%2Fwrite',
    )
    expect(await screen.findByRole('link', { name: 'Sign in' })).toBeInTheDocument()
  })
})
