import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ApiStatus } from './ApiStatus'

function mockFetch(status: number, body: unknown) {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('ApiStatus', () => {
  it('shows a loading state, then reports a healthy API', async () => {
    const fetchMock = mockFetch(200, { status: 'ok', database: 'ok' })

    render(<ApiStatus />)

    expect(screen.getByRole('status')).toHaveTextContent('Checking the API')
    expect(await screen.findByText('API and database are up')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/health', expect.anything())
  })

  it('reports an unavailable database when the API answers 503', async () => {
    mockFetch(503, { status: 'unavailable', database: 'unavailable' })

    render(<ApiStatus />)

    expect(
      await screen.findByText('API is up, but the database is unavailable'),
    ).toBeInTheDocument()
  })

  it('shows the server error message when the request fails', async () => {
    mockFetch(500, { error: { code: 'internal_error', message: 'Internal server error' } })

    render(<ApiStatus />)

    expect(await screen.findByText('API error: Internal server error')).toBeInTheDocument()
  })

  it('shows an error when the network is down', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    render(<ApiStatus />)

    expect(await screen.findByText('API unreachable. Is the backend running?')).toBeInTheDocument()
  })
})
