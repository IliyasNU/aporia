import type { ReactNode } from 'react'

import { errorMessage } from '../api/client'

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <p role="status" className="py-8 text-muted">
      {label}
    </p>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-4 text-red-900">
      <p>{errorMessage(error)}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="mt-2 font-medium underline">
          Try again
        </button>
      )}
    </div>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-md border border-dashed border-rule p-6 text-muted">{children}</div>
  )
}

/** Inline feedback after a form action, announced to screen readers. */
export function Notice({ kind, children }: { kind: 'success' | 'error'; children: ReactNode }) {
  const style =
    kind === 'success'
      ? 'border-accent/30 bg-accent/5 text-accent-strong'
      : 'border-red-200 bg-red-50 text-red-900'
  return (
    <p role={kind === 'error' ? 'alert' : 'status'} className={`rounded-md border p-3 ${style}`}>
      {children}
    </p>
  )
}
