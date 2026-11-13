import { useState, type FormEvent } from 'react'

import { ApiError, errorMessage } from '../api/client'
import { report, type ReportTarget } from '../api/social'
import { secondaryButton } from './buttons'
import { TextArea } from './Field'

/** "Report" link that opens a short form; reports go to the administrators (MOD-01). */
export function ReportButton({
  targetType,
  targetId,
}: {
  targetType: ReportTarget
  targetId: string
}) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [state, setState] = useState<{ kind: 'done' | 'error'; text: string } | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    try {
      await report(targetType, targetId, reason)
      setState({ kind: 'done', text: 'Thank you. An administrator will review it.' })
      setOpen(false)
    } catch (err) {
      const text =
        err instanceof ApiError && err.code === 'already_reported'
          ? 'You have already reported this.'
          : errorMessage(err)
      setState({ kind: 'error', text })
    } finally {
      setBusy(false)
    }
  }

  if (state?.kind === 'done') {
    return (
      <p role="status" className="text-sm text-muted">
        {state.text}
      </p>
    )
  }
  if (!open) {
    return (
      <button type="button" className="text-sm text-muted underline" onClick={() => setOpen(true)}>
        Report
      </button>
    )
  }
  return (
    <form onSubmit={submit} className="mt-2 space-y-2" aria-label={`Report this ${targetType}`}>
      <TextArea
        label={`Why should this ${targetType} be removed?`}
        rows={2}
        required
        maxLength={500}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      {state?.kind === 'error' && (
        <p role="alert" className="text-sm text-red-800">
          {state.text}
        </p>
      )}
      <div className="flex gap-2">
        <button
          type="submit"
          className={`${secondaryButton} text-sm`}
          disabled={busy || !reason.trim()}
        >
          Send report
        </button>
        <button type="button" className="text-sm underline" onClick={() => setOpen(false)}>
          Cancel
        </button>
      </div>
    </form>
  )
}
