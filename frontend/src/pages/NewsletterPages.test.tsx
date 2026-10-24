import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { tokenFromHash } from '../api/newsletter'
import { guest, makeMe, mockApi, page, renderApp } from '../test/api'

const author = {
  'GET /authors/socrates': {
    status: 200,
    body: {
      ...makeMe({ id: 'author-1', handle: 'socrates', display_name: 'Socrates' }),
      followed_by_me: false,
    },
  },
  'GET /articles': { status: 200, body: page([]) },
}

describe('Newsletter form on the author page', () => {
  it('subscribes a guest and shows the check-your-inbox message', async () => {
    const calls = mockApi({
      'GET /auth/me': guest,
      ...author,
      'POST /authors/author-1/newsletter-subscriptions': {
        status: 202,
        body: {
          message: 'Thanks! If this address can receive email, a confirmation link is on its way.',
        },
      },
    })
    renderApp('/authors/socrates')

    await userEvent.type(await screen.findByLabelText('Email address'), 'fan@example.com')
    await userEvent.click(screen.getByRole('button', { name: 'Subscribe' }))

    expect(await screen.findByText(/confirmation link is on its way/)).toBeInTheDocument()
    expect(screen.getByLabelText('Email address')).toHaveValue('')
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({ email: 'fan@example.com' })
  })

  it('explains an invalid address', async () => {
    mockApi({
      'GET /auth/me': guest,
      ...author,
      'POST /authors/author-1/newsletter-subscriptions': {
        status: 422,
        body: { error: { code: 'validation_error', message: 'Request validation failed' } },
      },
    })
    renderApp('/authors/socrates')

    await userEvent.type(await screen.findByLabelText('Email address'), 'nope')
    await userEvent.click(screen.getByRole('button', { name: 'Subscribe' }))

    expect(await screen.findByText('Please enter a valid email address.')).toBeInTheDocument()
  })

  it('is not shown on your own profile', async () => {
    mockApi({ 'GET /auth/me': { status: 200, body: makeMe({ id: 'author-1' }) }, ...author })
    renderApp('/authors/socrates')

    await screen.findByRole('heading', { name: 'Socrates' })
    expect(screen.queryByLabelText('Email address')).toBeNull()
  })
})

describe('Email link pages', () => {
  it('reads the token from the #fragment', () => {
    expect(tokenFromHash('#token=abc-123')).toBe('abc-123')
    expect(tokenFromHash('')).toBeNull()
  })

  it('confirms only after the button press', async () => {
    const calls = mockApi({
      'GET /auth/me': guest,
      'POST /newsletter/confirm': {
        status: 200,
        body: { author: { id: 'a', handle: 'socrates', display_name: 'Socrates' } },
      },
    })
    renderApp('/newsletter/confirm#token=secret-token')

    await screen.findByRole('button', { name: 'Confirm subscription' })
    expect(calls.some((c) => c.method === 'POST')).toBe(false)
    await userEvent.click(screen.getByRole('button', { name: 'Confirm subscription' }))

    expect(
      await screen.findByText('You are subscribed to Socrates’s new essays.'),
    ).toBeInTheDocument()
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({ token: 'secret-token' })
  })

  it('explains an expired confirmation link', async () => {
    mockApi({
      'GET /auth/me': guest,
      'POST /newsletter/confirm': {
        status: 400,
        body: {
          error: {
            code: 'invalid_token',
            message: 'This link is invalid or has expired. Please subscribe again.',
          },
        },
      },
    })
    renderApp('/newsletter/confirm#token=old')

    await userEvent.click(await screen.findByRole('button', { name: 'Confirm subscription' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('invalid or has expired')
  })

  it('unsubscribes without signing in', async () => {
    mockApi({ 'GET /auth/me': guest, 'POST /newsletter/unsubscribe': { status: 204 } })
    renderApp('/newsletter/unsubscribe#token=abc')

    await userEvent.click(await screen.findByRole('button', { name: 'Unsubscribe' }))

    expect(await screen.findByText(/You are unsubscribed/)).toBeInTheDocument()
  })

  it('handles a link without token', async () => {
    mockApi({ 'GET /auth/me': guest })
    renderApp('/newsletter/unsubscribe')

    expect(await screen.findByText(/This link is incomplete/)).toBeInTheDocument()
  })
})
