import { useState, type FormEvent } from 'react'
import { Link, useLocation } from 'react-router'

import { listMyArticles } from '../api/articles'
import { listBookmarks, listFollowing, unfollow } from '../api/social'
import { ApiError, errorMessage } from '../api/client'
import type { Me } from '../api/types'
import { listTags, setInterests, updateProfile } from '../api/users'
import { useAuth } from '../auth/context'
import { primaryButton, secondaryButton } from '../components/buttons'
import { TextArea, TextField } from '../components/Field'
import { Pagination } from '../components/Pagination'
import { Empty, ErrorState, Loading, Notice } from '../components/States'
import { useAsync } from '../hooks/useAsync'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { formatDate } from '../lib/format'

/** FE-05: the signed-in user's own area. Rendered inside <RequireAuth>. */
export function AccountPage() {
  useDocumentTitle('Your account')
  const { user, signOut } = useAuth()
  const location = useLocation()
  const notice = (location.state as { notice?: string } | null)?.notice
  const [signOutError, setSignOutError] = useState<string | null>(null)

  if (!user) return null

  async function onSignOut() {
    try {
      await signOut()
    } catch (err) {
      setSignOutError(errorMessage(err))
    }
  }

  return (
    <div className="space-y-12">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="font-serif text-3xl font-semibold">Your account</h1>
        <Link to={`/authors/${user.handle}`} className="text-accent-strong underline">
          View your public profile
        </Link>
      </div>
      {notice && <Notice kind="success">{notice}</Notice>}

      <MyArticles />
      <MyBookmarks />
      <MyFollowing />
      <ProfileForm user={user} />
      <InterestsForm user={user} />

      <section aria-labelledby="signout-heading" className="border-t border-rule pt-6">
        <h2 id="signout-heading" className="sr-only">
          Sign out
        </h2>
        {signOutError && <Notice kind="error">{signOutError}</Notice>}
        <button type="button" className={secondaryButton} onClick={onSignOut}>
          Sign out
        </button>
      </section>
    </div>
  )
}

function SectionHeading({ id, children }: { id: string; children: string }) {
  return (
    <h2 id={id} className="border-b border-rule pb-2 text-sm font-semibold tracking-wide uppercase">
      {children}
    </h2>
  )
}

function MyBookmarks() {
  const [page, setPage] = useState(1)
  const saved = useAsync(`bookmarks:${page}`, (signal) => listBookmarks(page, signal))
  return (
    <section aria-labelledby="bookmarks-heading">
      <SectionHeading id="bookmarks-heading">Saved essays</SectionHeading>
      {saved.status === 'loading' && <Loading />}
      {saved.status === 'error' && <ErrorState error={saved.error} onRetry={saved.reload} />}
      {saved.status === 'success' &&
        (saved.data.items.length === 0 ? (
          <p className="mt-4 text-muted">Use “Save” on an essay to keep it here.</p>
        ) : (
          <>
            <ul className="divide-y divide-rule">
              {saved.data.items.map((article) => (
                <li key={article.id} className="py-3">
                  <Link
                    to={`/articles/${encodeURIComponent(article.slug)}`}
                    className="font-medium hover:text-accent-strong"
                  >
                    {article.title}
                  </Link>
                  <span className="text-sm text-muted"> · {article.author.display_name}</span>
                </li>
              ))}
            </ul>
            <Pagination page={page} pageSize={20} total={saved.data.total} onChange={setPage} />
          </>
        ))}
    </section>
  )
}

function MyFollowing() {
  const following = useAsync('following-authors', listFollowing)
  const [error, setError] = useState<string | null>(null)

  async function stop(authorId: string) {
    setError(null)
    try {
      await unfollow(authorId)
      following.reload()
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <section aria-labelledby="following-heading">
      <SectionHeading id="following-heading">Authors you follow</SectionHeading>
      {error && <Notice kind="error">{error}</Notice>}
      {following.status === 'loading' && <Loading />}
      {following.status === 'error' && (
        <ErrorState error={following.error} onRetry={following.reload} />
      )}
      {following.status === 'success' &&
        (following.data.length === 0 ? (
          <p className="mt-4 text-muted">You do not follow anyone yet.</p>
        ) : (
          <ul className="divide-y divide-rule">
            {following.data.map(({ author }) => (
              <li key={author.id} className="flex items-center justify-between gap-2 py-3">
                <Link
                  to={`/authors/${author.handle}`}
                  className="font-medium hover:text-accent-strong"
                >
                  {author.display_name}
                </Link>
                <button
                  type="button"
                  className={`${secondaryButton} px-3 py-1 text-sm`}
                  onClick={() => stop(author.id)}
                  aria-label={`Unfollow ${author.display_name}`}
                >
                  Unfollow
                </button>
              </li>
            ))}
          </ul>
        ))}
    </section>
  )
}

function MyArticles() {
  const [page, setPage] = useState(1)
  const articles = useAsync(`my-articles:${page}`, (signal) => listMyArticles(page, signal))
  return (
    <section aria-labelledby="my-essays">
      <SectionHeading id="my-essays">Your essays</SectionHeading>
      {articles.status === 'loading' && <Loading />}
      {articles.status === 'error' && (
        <ErrorState error={articles.error} onRetry={articles.reload} />
      )}
      {articles.status === 'success' &&
        (articles.data.items.length === 0 ? (
          <div className="mt-4">
            <Empty>
              You have not written anything yet.{' '}
              <Link to="/write" className="font-medium text-accent-strong underline">
                Write your first essay
              </Link>
            </Empty>
          </div>
        ) : (
          <>
            <ul className="divide-y divide-rule">
              {articles.data.items.map((article) => (
                <li
                  key={article.id}
                  className="flex flex-wrap items-baseline justify-between gap-2 py-3"
                >
                  <Link
                    to={`/write/${article.id}`}
                    className="font-medium hover:text-accent-strong"
                  >
                    {article.title}
                  </Link>
                  <span className="text-sm text-muted">
                    {article.status} · edited {formatDate(article.updated_at)}
                    {article.status === 'published' && (
                      <>
                        {' · '}
                        <Link
                          to={`/articles/${encodeURIComponent(article.slug)}`}
                          className="text-accent-strong underline"
                        >
                          view
                        </Link>
                      </>
                    )}
                  </span>
                </li>
              ))}
            </ul>
            <Pagination page={page} pageSize={20} total={articles.data.total} onChange={setPage} />
          </>
        ))}
    </section>
  )
}

function ProfileForm({ user }: { user: Me }) {
  const { setUser } = useAuth()
  const [form, setForm] = useState({
    display_name: user.display_name,
    bio: user.bio,
    website: user.website ?? '',
  })
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [message, setMessage] = useState<{ kind: 'success' | 'error'; text: string } | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setMessage(null)
    setFieldErrors({})
    try {
      setUser(
        await updateProfile({
          display_name: form.display_name,
          bio: form.bio,
          website: form.website.trim() || null,
        }),
      )
      setMessage({ kind: 'success', text: 'Profile saved.' })
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) setFieldErrors(err.fieldErrors())
      setMessage({ kind: 'error', text: errorMessage(err) })
    } finally {
      setBusy(false)
    }
  }

  return (
    <section aria-labelledby="profile-heading">
      <SectionHeading id="profile-heading">Profile</SectionHeading>
      <form onSubmit={submit} className="mt-4 space-y-4" noValidate>
        {message && <Notice kind={message.kind}>{message.text}</Notice>}
        <TextField
          label="Display name"
          required
          maxLength={80}
          value={form.display_name}
          onChange={(e) => setForm({ ...form, display_name: e.target.value })}
          error={fieldErrors.display_name}
        />
        <TextArea
          label="Bio"
          rows={3}
          maxLength={500}
          value={form.bio}
          onChange={(e) => setForm({ ...form, bio: e.target.value })}
          error={fieldErrors.bio}
          hint={`${form.bio.length}/500`}
        />
        <TextField
          label="Website (optional)"
          type="url"
          placeholder="https://"
          maxLength={200}
          value={form.website}
          onChange={(e) => setForm({ ...form, website: e.target.value })}
          error={fieldErrors.website}
        />
        <p className="text-sm text-muted">
          Handle @{user.handle} and email {user.email} cannot be changed.
        </p>
        <button type="submit" className={primaryButton} disabled={busy}>
          {busy ? 'Saving…' : 'Save profile'}
        </button>
      </form>
    </section>
  )
}

function InterestsForm({ user }: { user: Me }) {
  const { setUser } = useAuth()
  const tags = useAsync('tags', listTags)
  const [selected, setSelected] = useState<string[]>(user.interests.map((t) => t.slug))
  const [message, setMessage] = useState<{ kind: 'success' | 'error'; text: string } | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setMessage(null)
    try {
      const { interests } = await setInterests(selected)
      setUser({ ...user, interests })
      setMessage({ kind: 'success', text: 'Interests saved.' })
    } catch (err) {
      setMessage({ kind: 'error', text: errorMessage(err) })
    } finally {
      setBusy(false)
    }
  }

  return (
    <section aria-labelledby="interests-heading">
      <SectionHeading id="interests-heading">Interests</SectionHeading>
      <p className="mt-2 text-sm text-muted">
        Topics you would like to read about. Only you can see them.
      </p>
      {tags.status === 'loading' && <Loading />}
      {tags.status === 'error' && <ErrorState error={tags.error} onRetry={tags.reload} />}
      {tags.status === 'success' && (
        <form onSubmit={submit} className="mt-4 space-y-4">
          {message && <Notice kind={message.kind}>{message.text}</Notice>}
          <fieldset className="flex flex-wrap gap-x-4 gap-y-2">
            <legend className="sr-only">Topics</legend>
            {tags.data.map((tag) => (
              <label key={tag.slug} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  className="size-4 accent-accent"
                  checked={selected.includes(tag.slug)}
                  onChange={() =>
                    setSelected((current) =>
                      current.includes(tag.slug)
                        ? current.filter((s) => s !== tag.slug)
                        : [...current, tag.slug],
                    )
                  }
                />
                {tag.name}
              </label>
            ))}
          </fieldset>
          <button type="submit" className={primaryButton} disabled={busy}>
            {busy ? 'Saving…' : 'Save interests'}
          </button>
        </form>
      )}
    </section>
  )
}
