import { useState } from 'react'
import { Link, useLocation } from 'react-router'

import { errorMessage } from '../api/client'
import { confirmSubscription, tokenFromHash, unsubscribe } from '../api/newsletter'
import { primaryButton } from '../components/buttons'
import { Notice } from '../components/States'
import { useDocumentTitle } from '../hooks/useDocumentTitle'

type Outcome = { kind: 'success' | 'error'; text: string }

/**
 * FE-07: the page behind an email link. Opening the link changes nothing; the
 * action only happens on the button press (a POST), so link scanners and
 * prefetching mail clients cannot confirm or cancel anything by themselves.
 */
function TokenAction(props: {
  title: string
  intro: string
  button: string
  run: (token: string) => Promise<string>
}) {
  useDocumentTitle(props.title)
  const { hash } = useLocation()
  const token = tokenFromHash(hash)
  const [outcome, setOutcome] = useState<Outcome | null>(null)
  const [busy, setBusy] = useState(false)

  async function act() {
    if (!token) return
    setBusy(true)
    try {
      setOutcome({ kind: 'success', text: await props.run(token) })
    } catch (err) {
      setOutcome({ kind: 'error', text: errorMessage(err) })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="font-serif text-3xl font-semibold">{props.title}</h1>
      {!token ? (
        <div className="mt-6">
          <Notice kind="error">
            This link is incomplete. Please open it again from the email.
          </Notice>
        </div>
      ) : outcome ? (
        <div className="mt-6 space-y-4">
          <Notice kind={outcome.kind}>{outcome.text}</Notice>
          <Link to="/" className="font-medium text-accent-strong underline">
            Go to Aporia
          </Link>
        </div>
      ) : (
        <>
          <p className="mt-4 text-muted">{props.intro}</p>
          <button type="button" className={`${primaryButton} mt-6`} disabled={busy} onClick={act}>
            {busy ? 'Working…' : props.button}
          </button>
        </>
      )}
    </div>
  )
}

export function ConfirmSubscriptionPage() {
  return (
    <TokenAction
      title="Confirm your subscription"
      intro="Confirm that you want to receive an email whenever this author publishes a new essay."
      button="Confirm subscription"
      run={async (token) => {
        const { author } = await confirmSubscription(token)
        return `You are subscribed to ${author.display_name}’s new essays.`
      }}
    />
  )
}

export function UnsubscribePage() {
  return (
    <TokenAction
      title="Unsubscribe"
      intro="Stop receiving emails about this author’s new essays. You do not need an account."
      button="Unsubscribe"
      run={async (token) => {
        await unsubscribe(token)
        return 'You are unsubscribed. No more emails will be sent for this subscription.'
      }}
    />
  )
}
