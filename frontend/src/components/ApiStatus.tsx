import { useEffect, useState } from 'react'

import { ApiError } from '../api/client'
import { fetchHealth, type Health } from '../api/health'

type State =
  { kind: 'loading' } | { kind: 'loaded'; health: Health } | { kind: 'error'; label: string }

function describe(state: State): { label: string; tone: 'neutral' | 'good' | 'bad' } {
  switch (state.kind) {
    case 'loading':
      return { label: 'Checking the API…', tone: 'neutral' }
    case 'error':
      return { label: state.label, tone: 'bad' }
    case 'loaded':
      return state.health.database === 'ok'
        ? { label: 'API and database are up', tone: 'good' }
        : { label: 'API is up, but the database is unavailable', tone: 'bad' }
  }
}

const dotColor = {
  neutral: 'bg-muted',
  good: 'bg-accent',
  bad: 'bg-red-700',
} as const

/** Live status of the backend, read from GET /api/v1/health. */
export function ApiStatus() {
  const [state, setState] = useState<State>({ kind: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    fetchHealth(controller.signal)
      .then((health) => setState({ kind: 'loaded', health }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        const label =
          error instanceof ApiError
            ? `API error: ${error.message}`
            : 'API unreachable. Is the backend running?'
        setState({ kind: 'error', label })
      })
    return () => controller.abort()
  }, [])

  const { label, tone } = describe(state)

  return (
    <p role="status" aria-live="polite" className="flex items-center gap-2 text-sm text-muted">
      <span aria-hidden="true" className={`inline-block size-2 rounded-full ${dotColor[tone]}`} />
      {label}
    </p>
  )
}
