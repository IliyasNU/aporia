import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router'

import { errorMessage } from '../api/client'
import { useAuth } from '../auth/context'
import { primaryButton } from '../components/buttons'
import { TextField } from '../components/Field'
import { Notice } from '../components/States'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { safeNext } from '../lib/redirect'

export function SignInPage() {
  useDocumentTitle('Sign in')
  const { user, signIn } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = safeNext(params.get('next'))
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to={next} replace />

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await signIn(email, password)
      navigate(next, { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="font-serif text-3xl font-semibold">Sign in</h1>
      <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
        {error && <Notice kind="error">{error}</Notice>}
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <TextField
          label="Password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit" className={primaryButton} disabled={busy}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
      <p className="mt-6 text-muted">
        New here?{' '}
        <Link
          to={`/signup?next=${encodeURIComponent(next)}`}
          className="font-medium text-accent-strong underline"
        >
          Create an account
        </Link>
      </p>
    </div>
  )
}
