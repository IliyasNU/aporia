import { useState, type FormEvent } from 'react'

import { ApiError, errorMessage } from '../api/client'
import { subscribeToAuthor } from '../api/newsletter'
import { secondaryButton } from './buttons'
import { Panel } from './Panel'
import { Notice } from './States'

/** MAIL-01: subscribe to an author's new essays by email; no account needed. */
export function NewsletterForm({ authorId, authorName }: { authorId: string; authorName: string }) {
  const [email, setEmail] = useState('')
  const [result, setResult] = useState<{ kind: 'success' | 'error'; text: string } | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setResult(null)
    try {
      const { message } = await subscribeToAuthor(authorId, email)
      setResult({ kind: 'success', text: message })
      setEmail('')
    } catch (err) {
      const text =
        err instanceof ApiError && err.status === 422
          ? 'Please enter a valid email address.'
          : errorMessage(err)
      setResult({ kind: 'error', text })
    } finally {
      setBusy(false)
    }
  }

  return (
    <Panel title="Email updates">
      <div className="p-4">
        <p className="text-sm text-muted">
          Get {authorName}’s new essays by email: one email per new essay, with an unsubscribe link
          in every message. No account needed.
        </p>
        <form onSubmit={submit} className="mt-3 flex flex-wrap gap-2" noValidate>
          <label htmlFor="newsletter-email" className="sr-only">
            Email address
          </label>
          <input
            id="newsletter-email"
            type="email"
            autoComplete="email"
            required
            maxLength={254}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="min-w-0 flex-1 rounded-sm border border-rule px-3 py-2"
          />
          <button type="submit" className={secondaryButton} disabled={busy || !email.trim()}>
            {busy ? 'Sending…' : 'Subscribe'}
          </button>
        </form>
        {result && (
          <div className="mt-3">
            <Notice kind={result.kind}>{result.text}</Notice>
          </div>
        )}
      </div>
    </Panel>
  )
}
