import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'

import {
  createArticle,
  deleteArticle,
  getMyArticle,
  publishArticle,
  unpublishArticle,
  updateArticle,
  type ArticleDraft,
} from '../api/articles'
import { ApiError, errorMessage } from '../api/client'
import type { Article } from '../api/types'
import { listTags } from '../api/users'
import { dangerButton, primaryButton, secondaryButton } from '../components/buttons'
import { TextArea, TextField } from '../components/Field'
import { Markdown } from '../components/Markdown'
import { ErrorState, Loading, Notice } from '../components/States'
import { useAsync } from '../hooks/useAsync'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { NotFoundPage } from './NotFoundPage'

const MAX_TAGS = 5

/** FE-04: write a new essay (/write) or edit one of yours (/write/:id). */
export function EditorPage() {
  const { id } = useParams()
  return id ? <LoadedEditor key={id} id={id} /> : <ArticleEditor key="new" article={null} />
}

function LoadedEditor({ id }: { id: string }) {
  const article = useAsync(`my-article:${id}`, (signal) => getMyArticle(id, signal))
  if (article.status === 'loading') return <Loading />
  if (article.status === 'error') {
    if (article.error instanceof ApiError && [403, 404].includes(article.error.status)) {
      return <NotFoundPage what="essay" />
    }
    return <ErrorState error={article.error} onRetry={article.reload} />
  }
  return <ArticleEditor article={article.data} />
}

type Action = 'save' | 'publish' | 'unpublish' | 'delete'

function ArticleEditor({ article: initial }: { article: Article | null }) {
  useDocumentTitle(initial ? `Editing: ${initial.title}` : 'New essay')
  const navigate = useNavigate()
  const location = useLocation()
  const tags = useAsync('tags', listTags)

  const [article, setArticle] = useState<Article | null>(initial)
  const [form, setForm] = useState<ArticleDraft>({
    title: initial?.title ?? '',
    summary: initial?.summary ?? '',
    body_markdown: initial?.body_markdown ?? '',
    tags: initial?.tags.map((t) => t.slug) ?? [],
  })
  const [mode, setMode] = useState<'write' | 'preview'>('write')
  const [busy, setBusy] = useState<Action | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [notice, setNotice] = useState<string | null>(
    (location.state as { notice?: string } | null)?.notice ?? null,
  )
  const [confirmingDelete, setConfirmingDelete] = useState(false)

  /** Runs an action. On failure the form keeps every character typed (FE-04). */
  async function run(action: Action, work: () => Promise<string | null>) {
    setBusy(action)
    setError(null)
    setFieldErrors({})
    setNotice(null)
    try {
      setNotice(await work())
    } catch (err) {
      if (err instanceof ApiError && err.status === 422 && err.details) {
        setFieldErrors(err.fieldErrors())
        setError('Please check the highlighted fields.')
      } else {
        setError(errorMessage(err))
      }
    } finally {
      setBusy(null)
    }
  }

  async function save(): Promise<Article> {
    const saved = article ? await updateArticle(article.id, form) : await createArticle(form)
    setArticle(saved)
    return saved
  }

  /** A new essay gets its own URL once saved, so a reload keeps working on it. */
  function moveToSavedUrl(saved: Article, message: string): string | null {
    if (article) return message
    navigate(`/write/${saved.id}`, { replace: true, state: { notice: message } })
    return null
  }

  const onSave = (event: FormEvent) => {
    event.preventDefault()
    void run('save', async () => moveToSavedUrl(await save(), 'Saved.'))
  }

  const onPublish = () =>
    run('publish', async () => {
      const saved = await save()
      const published = await publishArticle(saved.id)
      setArticle(published)
      return moveToSavedUrl(published, 'Published.')
    })

  const onUnpublish = () =>
    run('unpublish', async () => {
      if (!article) return null
      setArticle(await unpublishArticle(article.id))
      return 'Unpublished. Only you can see it now.'
    })

  const onDelete = () =>
    run('delete', async () => {
      if (!article) return null
      await deleteArticle(article.id)
      navigate('/account', { replace: true, state: { notice: `Deleted “${article.title}”.` } })
      return null
    })

  function toggleTag(slug: string) {
    setForm((current) => ({
      ...current,
      tags: current.tags.includes(slug)
        ? current.tags.filter((t) => t !== slug)
        : [...current.tags, slug],
    }))
  }

  const published = article?.status === 'published'
  const tab = (active: boolean) =>
    `rounded-t-md border-b-2 px-3 py-1.5 text-sm font-medium ${active ? 'border-accent text-accent-strong' : 'border-transparent text-muted'}`

  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="font-serif text-3xl font-semibold">
          {article ? 'Edit essay' : 'New essay'}
        </h1>
        {article && (
          <p className="text-sm text-muted">
            Status: <strong className="text-ink">{article.status}</strong>
            {published && (
              <>
                {' · '}
                <Link
                  to={`/articles/${encodeURIComponent(article.slug)}`}
                  className="text-accent-strong underline"
                >
                  View
                </Link>
              </>
            )}
          </p>
        )}
      </div>

      <form onSubmit={onSave} className="mt-6 space-y-5" noValidate>
        {notice && <Notice kind="success">{notice}</Notice>}
        {error && <Notice kind="error">{error}</Notice>}

        <TextField
          label="Title"
          required
          maxLength={200}
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          error={fieldErrors.title}
        />
        <TextArea
          label="Summary"
          rows={2}
          maxLength={300}
          value={form.summary}
          onChange={(e) => setForm({ ...form, summary: e.target.value })}
          error={fieldErrors.summary}
          hint={`One or two sentences for the essay list. ${form.summary.length}/300`}
        />

        <fieldset>
          <legend className="font-medium">Tags</legend>
          <p className="text-sm text-muted">Up to {MAX_TAGS}.</p>
          {tags.status === 'error' && <ErrorState error={tags.error} onRetry={tags.reload} />}
          {tags.status === 'success' && (
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2">
              {tags.data.map((tag) => {
                const checked = form.tags.includes(tag.slug)
                return (
                  <label key={tag.slug} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={!checked && form.tags.length >= MAX_TAGS}
                      onChange={() => toggleTag(tag.slug)}
                      className="size-4 accent-accent"
                    />
                    {tag.name}
                  </label>
                )
              })}
            </div>
          )}
          {fieldErrors.tags && <p className="mt-1 text-sm text-red-800">{fieldErrors.tags}</p>}
        </fieldset>

        <div>
          <div role="tablist" aria-label="Editor mode" className="flex gap-2 border-b border-rule">
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'write'}
              className={tab(mode === 'write')}
              onClick={() => setMode('write')}
            >
              Write
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'preview'}
              className={tab(mode === 'preview')}
              onClick={() => setMode('preview')}
            >
              Preview
            </button>
          </div>
          {mode === 'write' ? (
            <div className="mt-3">
              <TextArea
                label="Essay (Markdown)"
                rows={18}
                maxLength={100_000}
                value={form.body_markdown}
                onChange={(e) => setForm({ ...form, body_markdown: e.target.value })}
                error={fieldErrors.body_markdown}
                hint="Markdown: # heading, *italic*, **bold**, > quote, [link](https://…). HTML is not allowed."
              />
            </div>
          ) : (
            <div
              className="mt-3 min-h-40 rounded-md border border-rule bg-white p-4"
              aria-label="Preview"
            >
              {form.body_markdown.trim() ? (
                <Markdown source={form.body_markdown} />
              ) : (
                <p className="text-muted">Nothing to preview yet.</p>
              )}
            </div>
          )}
        </div>

        <div className="flex flex-wrap gap-3">
          <button type="submit" className={secondaryButton} disabled={busy !== null}>
            {busy === 'save' ? 'Saving…' : published ? 'Save changes' : 'Save draft'}
          </button>
          {!published && (
            <button
              type="button"
              className={primaryButton}
              disabled={busy !== null}
              onClick={onPublish}
            >
              {busy === 'publish' ? 'Publishing…' : 'Publish'}
            </button>
          )}
          {published && (
            <button
              type="button"
              className={secondaryButton}
              disabled={busy !== null}
              onClick={onUnpublish}
            >
              {busy === 'unpublish' ? 'Unpublishing…' : 'Unpublish'}
            </button>
          )}
          {article && !confirmingDelete && (
            <button
              type="button"
              className={dangerButton}
              disabled={busy !== null}
              onClick={() => setConfirmingDelete(true)}
            >
              Delete
            </button>
          )}
        </div>

        {article && confirmingDelete && (
          <div
            role="alertdialog"
            aria-labelledby="delete-question"
            className="rounded-md border border-red-300 bg-red-50 p-4"
          >
            <p id="delete-question" className="font-medium text-red-900">
              Delete “{article.title}”? Readers will no longer find it and you cannot restore it.
            </p>
            <div className="mt-3 flex gap-3">
              <button
                type="button"
                className={dangerButton}
                disabled={busy !== null}
                onClick={onDelete}
              >
                {busy === 'delete' ? 'Deleting…' : 'Yes, delete'}
              </button>
              <button
                type="button"
                className={secondaryButton}
                onClick={() => setConfirmingDelete(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </form>
    </div>
  )
}
