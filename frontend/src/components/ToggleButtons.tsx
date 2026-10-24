import { useState } from 'react'
import { Link, useLocation } from 'react-router'

import { errorMessage } from '../api/client'
import { bookmark, follow, unbookmark, unfollow } from '../api/social'
import { useAuth } from '../auth/context'
import { signInPath } from '../lib/redirect'
import { secondaryButton } from './buttons'

type ToggleProps = {
  initial: boolean
  on: () => Promise<void>
  off: () => Promise<void>
  labels: { on: string; off: string }
  description: string
}

/** A button for an on/off relation (follow, bookmark) stored by the API. */
function Toggle({ initial, on, off, labels, description }: ToggleProps) {
  const [active, setActive] = useState(initial)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function toggle() {
    setBusy(true)
    setError(null)
    try {
      await (active ? off() : on())
      setActive(!active)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <span className="inline-flex flex-col">
      <button
        type="button"
        aria-pressed={active}
        aria-label={description}
        disabled={busy}
        onClick={toggle}
        className={`${secondaryButton} px-3 py-1 text-sm ${active ? 'border-accent text-accent-strong' : ''}`}
      >
        {active ? labels.on : labels.off}
      </button>
      {error && (
        <span role="alert" className="mt-1 text-sm text-red-800">
          {error}
        </span>
      )}
    </span>
  )
}

/** Guests see a sign-in link instead of the button. */
function SignInInstead({ label }: { label: string }) {
  const location = useLocation()
  return (
    <Link to={signInPath(location.pathname)} className={`${secondaryButton} px-3 py-1 text-sm`}>
      {label}
    </Link>
  )
}

export function FollowButton(props: { authorId: string; authorName: string; initial: boolean }) {
  const { user } = useAuth()
  if (user === null) return <SignInInstead label="Follow" />
  if (!user || user.id === props.authorId) return null
  return (
    <Toggle
      initial={props.initial}
      on={() => follow(props.authorId)}
      off={() => unfollow(props.authorId)}
      labels={{ on: 'Following', off: 'Follow' }}
      description={`Follow ${props.authorName}`}
    />
  )
}

export function BookmarkButton(props: { articleId: string; initial: boolean }) {
  const { user } = useAuth()
  if (user === null) return <SignInInstead label="Save" />
  if (!user) return null
  return (
    <Toggle
      initial={props.initial}
      on={() => bookmark(props.articleId)}
      off={() => unbookmark(props.articleId)}
      labels={{ on: 'Saved', off: 'Save' }}
      description="Save this essay"
    />
  )
}
