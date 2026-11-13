import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { guest, makeArticle, makeMe, mockApi, page, renderApp } from '../test/api'

function feed(
  coldStart: boolean,
  items = [{ article: makeArticle(), reason: 'You follow Socrates', score: 0.6 }],
) {
  return { status: 200, body: { ...page(items as never[]), cold_start: coldStart } }
}

describe('ForYouPage', () => {
  it('shows each recommendation with its reason', async () => {
    mockApi({
      'GET /auth/me': { status: 200, body: makeMe() },
      'GET /feed/recommended': feed(false),
    })

    renderApp('/for-you')

    expect(await screen.findByRole('link', { name: 'On Doubt' })).toBeInTheDocument()
    expect(screen.getByText('You follow Socrates')).toBeInTheDocument()
    expect(screen.queryByRole('note')).toBeNull()
  })

  it('works for guests with a cold-start hint to sign in', async () => {
    mockApi({
      'GET /auth/me': guest,
      'GET /feed/recommended': feed(true, [
        { article: makeArticle(), reason: 'Recently published', score: 0.2 },
      ]),
    })

    renderApp('/for-you')

    expect(await screen.findByText('Recently published')).toBeInTheDocument()
    expect(screen.getByRole('note')).toHaveTextContent('Sign in and choose your interests')
  })

  it('asks signed-in readers without interests to choose some', async () => {
    mockApi({
      'GET /auth/me': { status: 200, body: makeMe() },
      'GET /feed/recommended': feed(true),
    })

    renderApp('/for-you')

    expect(await screen.findByRole('link', { name: 'Choose your interests' })).toHaveAttribute(
      'href',
      '/account',
    )
  })

  it('shows an empty state when nothing is published', async () => {
    mockApi({ 'GET /auth/me': guest, 'GET /feed/recommended': feed(true, []) })

    renderApp('/for-you')

    expect(await screen.findByText(/No essays to recommend yet/)).toBeInTheDocument()
  })
})
