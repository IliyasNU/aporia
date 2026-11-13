import { useState, type FormEvent } from 'react'
import { Link, useLocation } from 'react-router'

import { errorMessage } from '../api/client'
import { addComment, deleteComment, editComment, listComments } from '../api/social'
import type { Comment } from '../api/types'
import { useAuth } from '../auth/context'
import { useAsync } from '../hooks/useAsync'
import { signInPath } from '../lib/redirect'
import { dangerButton, primaryButton, secondaryButton } from './buttons'
import { TextArea } from './Field'
import { PostBox } from './PostBox'
import { ReportButton } from './ReportButton'
import { ErrorState, Loading, Notice } from './States'

/**
 * Flat comments under an essay (SOC-02), laid out like answers on Stack Exchange.
 * Comment text is plain text, never HTML.
 */
export function Comments({
  articleId,
  essayAuthorId,
}: {
  articleId: string
  essayAuthorId: string
}) {
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
    <section aria-labelledby="comments-heading" className="mt-6">
      <div className="flex items-baseline gap-2">
        <h2 id="comments-heading" className="text-[19px]">
          Comments
        </h2>
        {comments.status === 'success' && (
          <span className="text-[13px] text-muted">{comments.data.length}</span>
        )}
      </div>
      {comments.status === 'loading' && <Loading label="Loading comments…" />}
      {comments.status === 'error' && (
        <ErrorState error={comments.error} onRetry={comments.reload} />
      )}
      {comments.status === 'success' &&
        (comments.data.length === 0 ? (
          <p className="border-b border-rule py-4 text-muted">No comments yet.</p>
        ) : (
          <ol aria-label="Comments">
            {comments.data.map((comment, index) => (
              <CommentItem
                key={comment.id}
                number={index + 2}
                comment={comment}
                byEssayAuthor={comment.author.id === essayAuthorId}
                isOwn={user?.id === comment.author.id}
                canReport={Boolean(user) && user?.id !== comment.author.id}
                onChanged={comments.reload}
              />
            ))}
          </ol>
        ))}

      {user ? (
        <form onSubmit={submit} className="mt-6 space-y-3">
          {error && <Notice kind="error">{error}</Notice>}
          <TextArea
            label="Add a comment"
            rows={5}
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
          <p className="mt-6 text-[15px]">
            <Link to={signInPath(location.pathname)} className="text-accent hover:text-button">
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
  number: number
  comment: Comment
  byEssayAuthor: boolean
  isOwn: boolean
  canReport: boolean
  onChanged: () => void
}

function CommentItem({ number, comment, byEssayAuthor, isOwn, canReport, onChanged }: ItemProps) {
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

  const link = 'text-muted hover:text-ink'
  return (
    <li>
      <PostBox
        number={number}
        author={comment.author}
        byEssayAuthor={byEssayAuthor}
        verb="commented"
        postedAt={comment.created_at}
        footer={
          <>
            {isOwn && mode === 'view' && (
              <>
                <button type="button" className={link} onClick={() => setMode('edit')}>
                  Edit
                </button>
                <button type="button" className={link} onClick={() => setMode('confirm-delete')}>
                  Delete
                </button>
              </>
            )}
            {isOwn && mode === 'confirm-delete' && (
              <span
                role="alertdialog"
                aria-label="Delete comment?"
                className="flex items-center gap-2"
              >
                Delete this comment?
                <button
                  type="button"
                  className={dangerButton}
                  disabled={busy}
                  onClick={() => run(() => deleteComment(comment.id))}
                >
                  Yes, delete
                </button>
                <button type="button" className={link} onClick={() => setMode('view')}>
                  Cancel
                </button>
              </span>
            )}
            {canReport && <ReportButton targetType="comment" targetId={comment.id} />}
          </>
        }
      >
        {error && <Notice kind="error">{error}</Notice>}
        {mode === 'edit' ? (
          <form
            className="space-y-2"
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
            <div className="flex items-center gap-3">
              <button type="submit" className={secondaryButton} disabled={busy || !draft.trim()}>
                Save
              </button>
              <button type="button" className={link} onClick={() => setMode('view')}>
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <p className="text-[15px] leading-relaxed whitespace-pre-line">{comment.text}</p>
        )}
      </PostBox>
    </li>
  )
}
