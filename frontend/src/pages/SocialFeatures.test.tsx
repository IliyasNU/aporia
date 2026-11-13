import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import {
  guest,
  makeArticle,
  makeComment,
  makeMe,
  mockApi,
  page,
  renderApp,
  tagCatalog,
} from '../test/api'

const reader = { 'GET /auth/me': { status: 200, body: makeMe({ id: 'user-1' }) } }

function articleRoutes(overrides = {}) {
  return {
    'GET /articles/on-doubt': { status: 200, body: makeArticle(overrides) },
    'GET /articles/article-1/comments': { status: 200, body: [makeComment()] },
  }
}

describe('Article social controls', () => {
  it('saves and unsaves an essay', async () => {
    const calls = mockApi({
      ...reader,
      ...articleRoutes(),
      'POST /articles/article-1/bookmark': { status: 204 },
      'DELETE /articles/article-1/bookmark': { status: 204 },
    })
    renderApp('/articles/on-doubt')

    const save = await screen.findByRole('button', { name: 'Save this essay' })
    expect(save).toHaveAttribute('aria-pressed', 'false')
    await userEvent.click(save)
    expect(save).toHaveAttribute('aria-pressed', 'true')
    expect(save).toHaveTextContent('Saved')
    await userEvent.click(save)
    expect(save).toHaveAttribute('aria-pressed', 'false')

    expect(calls.filter((c) => c.path.endsWith('/bookmark')).map((c) => c.method)).toEqual([
      'POST',
      'DELETE',
    ])
  })

  it('follows the author and reflects the current state', async () => {
    mockApi({
      ...reader,
      ...articleRoutes({ following_author: true }),
      'DELETE /authors/author-1/follow': { status: 204 },
    })
    renderApp('/articles/on-doubt')

    const followButton = await screen.findByRole('button', { name: 'Follow Socrates' })
    expect(followButton).toHaveTextContent('Following')
    await userEvent.click(followButton)
    expect(followButton).toHaveTextContent('Follow')
  })

  it('shows sign-in links instead of buttons to guests', async () => {
    mockApi({ 'GET /auth/me': guest, ...articleRoutes() })
    renderApp('/articles/on-doubt')

    expect(await screen.findByRole('link', { name: 'Save' })).toHaveAttribute(
      'href',
      '/signin?next=%2Farticles%2Fon-doubt',
    )
    expect(screen.getByRole('link', { name: 'Follow' })).toBeInTheDocument()
    expect(await screen.findByText('to comment.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Report' })).toBeNull()
  })

  it('shows an error and keeps the state when the API fails', async () => {
    mockApi({
      ...reader,
      ...articleRoutes(),
      'POST /articles/article-1/bookmark': {
        status: 404,
        body: { error: { code: 'not_found', message: 'Article not found' } },
      },
    })
    renderApp('/articles/on-doubt')

    const save = await screen.findByRole('button', { name: 'Save this essay' })
    await userEvent.click(save)

    expect(await screen.findByText('Article not found')).toBeInTheDocument()
    expect(save).toHaveAttribute('aria-pressed', 'false')
  })

  it('tells the author when a moderator hid the essay and hides social controls', async () => {
    mockApi({
      'GET /auth/me': { status: 200, body: makeMe({ id: 'author-1' }) },
      ...articleRoutes({ moderation_status: 'hidden' }),
    })
    renderApp('/articles/on-doubt')

    expect(
      await screen.findByText('Hidden by a moderator: readers cannot see this essay.'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Comments' })).toBeNull()
  })
})

describe('Comments', () => {
  it('lists comments as plain text and posts a new one', async () => {
    let comments = [makeComment({ text: '<b>not bold</b>' })]
    mockApi({
      ...reader,
      'GET /articles/on-doubt': { status: 200, body: makeArticle() },
      'GET /articles/article-1/comments': () => ({ status: 200, body: comments }),
      'POST /articles/article-1/comments': (body) => {
        const created = makeComment({
          id: 'comment-2',
          text: (body as { text: string }).text,
          author: { id: 'user-1', handle: 'ada', display_name: 'Ada Lovelace' },
        })
        comments = [...comments, created]
        return { status: 201, body: created }
      },
    })
    renderApp('/articles/on-doubt')

    expect(await screen.findByText('<b>not bold</b>')).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText('Add a comment'), 'A fine point.')
    await userEvent.click(screen.getByRole('button', { name: 'Post comment' }))

    expect(await screen.findByText('A fine point.')).toBeInTheDocument()
    expect(screen.getByLabelText('Add a comment')).toHaveValue('')
  })

  it('lets authors edit and delete their own comments, with confirmation', async () => {
    const own = makeComment({ author: { id: 'user-1', handle: 'ada', display_name: 'Ada' } })
    const calls = mockApi({
      ...reader,
      'GET /articles/on-doubt': { status: 200, body: makeArticle() },
      'GET /articles/article-1/comments': { status: 200, body: [own] },
      'PATCH /comments/comment-1': { status: 200, body: { ...own, text: 'Edited' } },
      'DELETE /comments/comment-1': { status: 204 },
    })
    renderApp('/articles/on-doubt')

    await userEvent.click(await screen.findByRole('button', { name: 'Edit' }))
    const box = screen.getByLabelText('Edit comment')
    await userEvent.clear(box)
    await userEvent.type(box, 'Edited')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(calls.some((c) => c.method === 'PATCH')).toBe(true))

    await userEvent.click(screen.getByRole('button', { name: 'Delete' }))
    expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
    await userEvent.click(screen.getByRole('button', { name: 'Yes, delete' }))
    await waitFor(() => expect(calls.some((c) => c.method === 'DELETE')).toBe(true))
    expect(calls.find((c) => c.method === 'PATCH')?.body).toEqual({ text: 'Edited' })
  })

  it("reports someone else's comment once", async () => {
    let reported = false
    mockApi({
      ...reader,
      'GET /articles/on-doubt': { status: 200, body: makeArticle() },
      'GET /articles/article-1/comments': { status: 200, body: [makeComment()] },
      'POST /reports': () =>
        reported
          ? {
              status: 409,
              body: { error: { code: 'already_reported', message: 'Already reported' } },
            }
          : ((reported = true), { status: 201, body: {} }),
    })
    renderApp('/articles/on-doubt')

    const comment = (await screen.findByText('Well argued.')).closest('li')!
    await userEvent.click(within(comment).getByRole('button', { name: 'Report' }))
    await userEvent.type(within(comment).getByLabelText(/Why should this comment/), 'Spam')
    await userEvent.click(within(comment).getByRole('button', { name: 'Send report' }))

    expect(
      await within(comment).findByText('Thank you. An administrator will review it.'),
    ).toBeInTheDocument()
  })
})

describe('Feeds', () => {
  it('sorts the home page by most saved', async () => {
    const calls = mockApi({
      'GET /auth/me': guest,
      'GET /articles': { status: 200, body: page([makeArticle()]) },
      'GET /tags': { status: 200, body: tagCatalog },
    })
    renderApp('/')

    await userEvent.selectOptions(await screen.findByLabelText('Sort by'), 'popular')

    await waitFor(() =>
      expect(calls.map((c) => c.path)).toContain('/articles?sort=popular&page=1&page_size=10'),
    )
  })

  it('shows the following feed, or how to fill it', async () => {
    mockApi({ ...reader, 'GET /feed/following': { status: 200, body: page([]) } })
    renderApp('/following')

    expect(await screen.findByText(/Nothing here yet/)).toBeInTheDocument()
  })

  it('lists followed authors and unfollows from the account page', async () => {
    let following = [
      { author: { id: 'author-1', handle: 'socrates', display_name: 'Socrates' }, created_at: '' },
    ]
    mockApi({
      ...reader,
      'GET /tags': { status: 200, body: tagCatalog },
      'GET /me/articles': { status: 200, body: page([]) },
      'GET /me/bookmarks': { status: 200, body: page([makeArticle({ title: 'Saved one' })]) },
      'GET /me/following': () => ({ status: 200, body: following }),
      'DELETE /authors/author-1/follow': () => ((following = []), { status: 204 }),
    })
    renderApp('/account')

    expect(await screen.findByRole('link', { name: 'Saved one' })).toBeInTheDocument()
    await userEvent.click(await screen.findByRole('button', { name: 'Unfollow Socrates' }))
    expect(await screen.findByText('You do not follow anyone yet.')).toBeInTheDocument()
  })
})
