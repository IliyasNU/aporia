import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { guest, makeMe, mockApi, page, renderApp, tagCatalog } from '../test/api'

const homeRoutes = {
  'GET /articles': { status: 200, body: page([]) },
  'GET /tags': { status: 200, body: tagCatalog },
}

describe('Sign in', () => {
  it('shows the server message for wrong credentials and keeps the email', async () => {
    mockApi({
      'GET /auth/me': guest,
      'POST /auth/login': {
        status: 401,
        body: { error: { code: 'invalid_credentials', message: 'Invalid email or password' } },
      },
    })
    renderApp('/signin')

    await userEvent.type(await screen.findByLabelText('Email'), 'ada@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password')
    expect(screen.getByLabelText('Email')).toHaveValue('ada@example.com')
  })

  it('returns to the requested page after signing in', async () => {
    const calls = mockApi({
      'GET /auth/me': guest,
      'POST /auth/login': { status: 200, body: makeMe() },
      'GET /me/articles': { status: 200, body: page([]) },
      ...homeRoutes,
    })
    renderApp('/signin?next=%2Faccount')

    await userEvent.type(await screen.findByLabelText('Email'), 'ada@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'correct horse')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { name: 'Your account' })).toBeInTheDocument()
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
      email: 'ada@example.com',
      password: 'correct horse',
    })
  })

  it('ignores redirects to other sites', async () => {
    mockApi({
      'GET /auth/me': guest,
      'POST /auth/login': { status: 200, body: makeMe() },
      ...homeRoutes,
    })
    renderApp('/signin?next=%2F%2Fevil.example')

    await userEvent.type(await screen.findByLabelText('Email'), 'ada@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'correct horse')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { name: 'Essays' })).toBeInTheDocument()
  })
})

describe('Sign up', () => {
  it('shows a taken email next to the email field', async () => {
    mockApi({
      'GET /auth/me': guest,
      'POST /auth/register': {
        status: 409,
        body: {
          error: { code: 'email_taken', message: 'An account with this email already exists' },
        },
      },
    })
    renderApp('/signup')

    await userEvent.type(await screen.findByLabelText('Email'), 'ada@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'correct horse')
    await userEvent.type(screen.getByLabelText('Handle'), 'ada')
    await userEvent.type(screen.getByLabelText('Display name'), 'Ada')
    await userEvent.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByText('An account with this email already exists')).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toHaveAttribute('aria-invalid', 'true')
  })

  it('takes a new account to its personal area', async () => {
    mockApi({
      'GET /auth/me': guest,
      'POST /auth/register': { status: 201, body: makeMe() },
      'GET /me/articles': { status: 200, body: page([]) },
      'GET /tags': { status: 200, body: tagCatalog },
    })
    renderApp('/signup')

    await userEvent.type(await screen.findByLabelText('Email'), 'ada@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'correct horse')
    await userEvent.type(screen.getByLabelText('Handle'), 'ada')
    await userEvent.type(screen.getByLabelText('Display name'), 'Ada')
    await userEvent.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByRole('heading', { name: 'Your account' })).toBeInTheDocument()
  })
})
