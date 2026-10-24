import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { guest, makeArticle, makeMe, mockApi, page, renderApp, tagCatalog } from '../test/api'

const signedIn = { 'GET /auth/me': { status: 200, body: makeMe({ id: 'author-1' }) } }

describe('EditorPage', () => {
  it('sends guests to sign in first', async () => {
    mockApi({ 'GET /auth/me': guest })

    renderApp('/write')

    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('keeps everything typed when the server fails', async () => {
    mockApi({
      ...signedIn,
      'GET /tags': { status: 200, body: tagCatalog },
      'POST /articles': {
        status: 500,
        body: { error: { code: 'internal_error', message: 'Internal server error' } },
      },
    })
    renderApp('/write')

    await userEvent.type(await screen.findByLabelText('Title'), 'My essay')
    await userEvent.type(screen.getByLabelText('Essay (Markdown)'), 'Long thoughts')
    await userEvent.click(screen.getByRole('button', { name: 'Save draft' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Internal server error')
    expect(screen.getByLabelText('Title')).toHaveValue('My essay')
    expect(screen.getByLabelText('Essay (Markdown)')).toHaveValue('Long thoughts')
  })

  it('previews Markdown without saving', async () => {
    mockApi({ ...signedIn, 'GET /tags': { status: 200, body: tagCatalog } })
    renderApp('/write')

    await userEvent.type(await screen.findByLabelText('Essay (Markdown)'), '## Part one')
    await userEvent.click(screen.getByRole('tab', { name: 'Preview' }))

    expect(screen.getByRole('heading', { level: 2, name: 'Part one' })).toBeInTheDocument()
  })

  it('publishes a new essay and moves to its own editor URL', async () => {
    const created = makeArticle({ status: 'draft', published_at: null })
    const published = makeArticle()
    const calls = mockApi({
      ...signedIn,
      'GET /tags': { status: 200, body: tagCatalog },
      'POST /articles': { status: 201, body: created },
      'POST /articles/article-1/publish': { status: 200, body: published },
      'GET /me/articles/article-1': { status: 200, body: published },
    })
    renderApp('/write')

    await userEvent.type(await screen.findByLabelText('Title'), 'On Doubt')
    await userEvent.type(screen.getByLabelText('Essay (Markdown)'), 'Text')
    await userEvent.click(await screen.findByRole('checkbox', { name: 'Logic' }))
    await userEvent.click(screen.getByRole('button', { name: 'Publish' }))

    expect(await screen.findByText('Published.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'View' })).toHaveAttribute('href', '/articles/on-doubt')
    expect(calls.find((c) => c.method === 'POST' && c.path === '/articles')?.body).toEqual({
      title: 'On Doubt',
      summary: '',
      body_markdown: 'Text',
      tags: ['logic'],
    })
  })

  it('asks for confirmation before deleting', async () => {
    const calls = mockApi({
      ...signedIn,
      'GET /tags': { status: 200, body: tagCatalog },
      'GET /me/articles/article-1': { status: 200, body: makeArticle() },
      'DELETE /articles/article-1': { status: 204 },
      'GET /me/articles': { status: 200, body: page([]) },
    })
    renderApp('/write/article-1')

    await userEvent.click(await screen.findByRole('button', { name: 'Delete' }))
    expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(calls.some((c) => c.method === 'DELETE')).toBe(false)

    await userEvent.click(screen.getByRole('button', { name: 'Delete' }))
    await userEvent.click(screen.getByRole('button', { name: 'Yes, delete' }))

    await waitFor(() => expect(calls.some((c) => c.method === 'DELETE')).toBe(true))
    expect(await screen.findByText('Deleted “On Doubt”.')).toBeInTheDocument()
  })

  it("does not open someone else's essay", async () => {
    mockApi({
      ...signedIn,
      'GET /tags': { status: 200, body: tagCatalog },
      'GET /me/articles/article-9': {
        status: 403,
        body: { error: { code: 'forbidden', message: 'You can only change your own articles' } },
      },
    })

    renderApp('/write/article-9')

    expect(
      await screen.findByRole('heading', { name: 'This essay does not exist' }),
    ).toBeInTheDocument()
  })
})
