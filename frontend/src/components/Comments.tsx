import { useState, type FormEvent } from 'react'
import { Link, useLocation } from 'react-router'

import { errorMessage } from '../api/client'
import { addComment, deleteComment, editComment, listComments } from '../api/social'
import type { Comment } from '../api/types'
import { useAuth } from '../auth/context'
import { useAsync } from '../hooks/useAsync'
import { formatDate } from '../lib/format'
import { signInPath } from '../lib/redirect'
import { dangerButton, primaryButton, secondaryButton } from './buttons'
import { TextArea } from './Field'
import { ReportButton } from './ReportButton'
import { ErrorState, Loading, Notice } from './States'

/** Flat comments under an essay (SOC-02). Comment text is plain text, never HTML. */
export function Comments({ articleId }: { articleId: string }) {
  const { user } = useAuth()
  const location = useLocation()
  const comments = useAsync(`comments:${articleId}`, (signal) => listComments(articleId, signal))
  const [text, setText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await addComment(articleId, text)
      setText('')
      comments.reload()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section aria-labelledby="comments-heading" className="mt-12 border-t border-rule pt-8">
      <h2 id="comments-heading" className="font-serif text-2xl font-semibold">
        Comments
      </h2>
      {comments.status === 'loading' && <Loading label="Loading comments…" />}
      {comments.status === 'error' && (
        <ErrorState error={comments.error} onRetry={comments.reload} />
      )}
      {comments.status === 'success' &&
        (comments.data.length === 0 ? (
          <p className="mt-4 text-muted">No comments yet.</p>
        ) : (
          <ul className="mt-4 divide-y divide-rule">
            {comments.data.map((comment) => (
              <CommentItem
                key={comment.id}
                comment={comment}
                isOwn={user?.id === comment.author.id}
                canReport={Boolean(user) && user?.id !== comment.author.id}
                onChanged={comments.reload}
              />
            ))}
          </ul>
        ))}

      {user ? (
        <form onSubmit={submit} className="mt-6 space-y-3">
          {error && <Notice kind="error">{error}</Notice>}
          <TextArea
            label="Add a comment"
            rows={3}
            maxLength={2000}
            required
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <button type="submit" className={primaryButton} disabled={busy || !text.trim()}>
            {busy ? 'Posting…' : 'Post comment'}
          </button>
        </form>
      ) : (
        user === null && (
          <p className="mt-6 text-muted">
            <Link
              to={signInPath(location.pathname)}
              className="font-medium text-accent-strong underline"
            >
              Sign in
            </Link>{' '}
            to comment.
          </p>
        )
      )}
    </section>
  )
}

type ItemProps = {
  comment: Comment
  isOwn: boolean
  canReport: boolean
  onChanged: () => void
}

function CommentItem({ comment, isOwn, canReport, onChanged }: ItemProps) {
  const [mode, setMode] = useState<'view' | 'edit' | 'confirm-delete'>('view')
  const [draft, setDraft] = useState(comment.text)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function run(work: () => Promise<unknown>) {
    setBusy(true)
    setError(null)
    try {
      await work()
      setMode('view')
      onChanged()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className="py-4">
      <p className="text-sm text-muted">
        <Link
          to={`/authors/${comment.author.handle}`}
          className="font-medium text-ink hover:underline"
        >
          {comment.author.display_name}
        </Link>
        {' · '}
        <time dateTime={comment.created_at}>{formatDate(comment.created_at)}</time>
      </p>
      {error && <Notice kind="error">{error}</Notice>}
      {mode === 'edit' ? (
        <form
          className="mt-2 space-y-2"
          onSubmit={(e) => {
            e.preventDefault()
            void run(() => editComment(comment.id, draft))
          }}
        >
          <TextArea
            label="Edit comment"
            rows={3}
            maxLength={2000}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
          <div className="flex gap-2">
            <button
              type="submit"
              className={`${secondaryButton} text-sm`}
              disabled={busy || !draft.trim()}
            >
              Save
            </button>
            <button type="button" className="text-sm underline" onClick={() => setMode('view')}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <p className="mt-1 whitespace-pre-line">{comment.text}</p>
      )}
      <div className="mt-2 flex flex-wrap items-center gap-3">
        {isOwn && mode === 'view' && (
          <>
            <button
              type="button"
              className="text-sm text-muted underline"
              onClick={() => setMode('edit')}
            >
              Edit
            </button>
            <button
              type="button"
              className="text-sm text-muted underline"
              onClick={() => setMode('confirm-delete')}
            >
              Delete
            </button>
          </>
        )}
        {isOwn && mode === 'confirm-delete' && (
          <span
            role="alertdialog"
            aria-label="Delete comment?"
            className="flex items-center gap-2 text-sm"
          >
            Delete this comment?
            <button
              type="button"
              className={`${dangerButton} px-2 py-1 text-sm`}
              disabled={busy}
              onClick={() => run(() => deleteComment(comment.id))}
            >
              Yes, delete
            </button>
            <button type="button" className="underline" onClick={() => setMode('view')}>
              Cancel
            </button>
          </span>
        )}
        {canReport && <ReportButton targetType="comment" targetId={comment.id} />}
      </div>
    </li>
  )
}
