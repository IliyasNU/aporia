import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { guest, mockApi, page, renderApp, tagCatalog } from '../test/api'

describe('Policy pages', () => {
  it('are linked from every page footer', async () => {
    mockApi({
      'GET /auth/me': guest,
      'GET /articles': { status: 200, body: page([]) },
      'GET /tags': { status: 200, body: tagCatalog },
    })
    renderApp('/')

    await userEvent.click(await screen.findByRole('link', { name: 'Privacy' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Privacy' })).toBeInTheDocument()
    expect(screen.getByText(/do not record which essays you open/)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('link', { name: 'Publication rules' }))
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Publication rules' }),
    ).toBeInTheDocument()
  })

  it('are mentioned on the sign-up form', async () => {
    mockApi({ 'GET /auth/me': guest })
    renderApp('/signup')

    expect(await screen.findByRole('link', { name: 'privacy notice' })).toHaveAttribute(
      'href',
      '/privacy',
    )
  })
})
