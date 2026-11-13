import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { guest, mockApi, page, renderApp, tagCatalog } from './test/api'

describe('App navigation', () => {
  it('survives client-side navigation when scrollTo returns a Promise (as in Chromium)', async () => {
    vi.stubGlobal(
      'scrollTo',
      vi.fn(() => Promise.resolve()),
    )
    mockApi({
      'GET /auth/me': guest,
      'GET /articles': { status: 200, body: page([]) },
      'GET /tags': { status: 200, body: tagCatalog },
    })
    renderApp('/')

    await userEvent.click(await screen.findByRole('link', { name: 'Sign up' }))
    await userEvent.click(await screen.findByRole('link', { name: 'Essays' }))

    expect(await screen.findByRole('heading', { name: 'Essays' })).toBeInTheDocument()
  })
})
