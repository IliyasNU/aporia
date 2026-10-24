import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { makeArticle, makeMe, mockApi, page, renderApp, tagCatalog } from '../test/api'

describe('AccountPage', () => {
  it('lists own essays in every status with edit links', async () => {
    mockApi({
      'GET /auth/me': { status: 200, body: makeMe() },
      'GET /tags': { status: 200, body: tagCatalog },
      'GET /me/articles': {
        status: 200,
        body: page([makeArticle({ status: 'draft', title: 'Unfinished', published_at: null })]),
      },
    })

    renderApp('/account')

    expect(await screen.findByRole('link', { name: 'Unfinished' })).toHaveAttribute(
      'href',
      '/write/article-1',
    )
    expect(screen.getByText(/draft · edited/)).toBeInTheDocument()
  })

  it('saves profile and interests through the API', async () => {
    const calls = mockApi({
      'GET /auth/me': { status: 200, body: makeMe() },
      'GET /tags': { status: 200, body: tagCatalog },
      'GET /me/articles': { status: 200, body: page([]) },
      'GET /me/bookmarks': { status: 200, body: page([]) },
      'GET /me/following': { status: 200, body: [] },
      'PATCH /me/profile': (body) => ({ status: 200, body: makeMe(body as object) }),
      'PUT /me/interests': {
        status: 200,
        body: { interests: [{ slug: 'logic', name: 'Logic' }] },
      },
    })
    renderApp('/account')

    const bio = await screen.findByLabelText('Bio')
    await userEvent.type(bio, 'Poetical science.')
    await userEvent.click(screen.getByRole('button', { name: 'Save profile' }))
    expect(await screen.findByText('Profile saved.')).toBeInTheDocument()

    await userEvent.click(await screen.findByRole('checkbox', { name: 'Logic' }))
    await userEvent.click(screen.getByRole('button', { name: 'Save interests' }))
    expect(await screen.findByText('Interests saved.')).toBeInTheDocument()

    expect(calls.find((c) => c.method === 'PATCH')?.body).toEqual({
      display_name: 'Ada Lovelace',
      bio: 'Poetical science.',
      website: null,
    })
    expect(calls.find((c) => c.method === 'PUT')?.body).toEqual({ tags: ['logic'] })
  })

  it('signs out and returns to the home page', async () => {
    const calls = mockApi({
      'GET /auth/me': { status: 200, body: makeMe() },
      'GET /tags': { status: 200, body: tagCatalog },
      'GET /me/articles': { status: 200, body: page([]) },
      'GET /me/bookmarks': { status: 200, body: page([]) },
      'GET /me/following': { status: 200, body: [] },
      'POST /auth/logout': { status: 204 },
      'GET /articles': { status: 200, body: page([]) },
    })
    renderApp('/account')

    await userEvent.click(await screen.findByRole('button', { name: 'Sign out' }))

    expect(await screen.findByRole('heading', { name: 'Essays' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Sign in' })).toBeInTheDocument()
    expect(calls.some((c) => c.method === 'POST' && c.path === '/auth/logout')).toBe(true)
  })
})
