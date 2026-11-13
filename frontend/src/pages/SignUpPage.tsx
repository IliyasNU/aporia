import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router'

import { ApiError, errorMessage } from '../api/client'
import { useAuth } from '../auth/context'
import { primaryButton } from '../components/buttons'
import { TextField } from '../components/Field'
import { Notice } from '../components/States'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { safeNext } from '../lib/redirect'

const conflictFields: Record<string, string> = { email_taken: 'email', handle_taken: 'handle' }

export function SignUpPage() {
  useDocumentTitle('Sign up')
  const { user, signUp } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = safeNext(params.get('next'))
  // New accounts start in their personal area (to pick interests) unless they
  // came from a specific page.
  const destination = next === '/' ? '/account' : next
  const [form, setForm] = useState({ email: '', password: '', handle: '', display_name: '' })
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to={destination} replace />

  const set = (field: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm({ ...form, [field]: e.target.value })

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    setFieldErrors({})
    try {
      await signUp(form)
      navigate(destination, { replace: true })
    } catch (err) {
      if (err instanceof ApiError && err.code in conflictFields) {
        setFieldErrors({ [conflictFields[err.code]!]: err.message })
      } else if (err instanceof ApiError && err.status === 422) {
        setFieldErrors(err.fieldErrors())
        setError('Please check the highlighted fields.')
      } else {
        setError(errorMessage(err))
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="font-serif text-3xl font-semibold">Create an account</h1>
      <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
        {error && <Notice kind="error">{error}</Notice>}
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={form.email}
          onChange={set('email')}
          error={fieldErrors.email}
        />
        <TextField
          label="Password"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          maxLength={128}
          value={form.password}
          onChange={set('password')}
          error={fieldErrors.password}
          hint="At least 8 characters. A short sentence works well."
        />
        <TextField
          label="Handle"
          autoComplete="username"
          required
          maxLength={30}
          value={form.handle}
          onChange={set('handle')}
          error={fieldErrors.handle}
          hint="Your public address: letters, digits and underscores, 3–30 characters."
        />
        <TextField
          label="Display name"
          autoComplete="name"
          required
          maxLength={80}
          value={form.display_name}
          onChange={set('display_name')}
          error={fieldErrors.display_name}
        />
        <p className="text-sm text-muted">
          By creating an account you agree to the{' '}
          <Link to="/rules" className="underline">
            publication rules
          </Link>{' '}
          and the{' '}
          <Link to="/privacy" className="underline">
            privacy notice
          </Link>
          .
        </p>
        <button type="submit" className={primaryButton} disabled={busy}>
          {busy ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p className="mt-6 text-muted">
        Already have an account?{' '}
        <Link
          to={`/signin?next=${encodeURIComponent(next)}`}
          className="font-medium text-accent-strong underline"
        >
          Sign in
        </Link>
      </p>
    </div>
  )
}
