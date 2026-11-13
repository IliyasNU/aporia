import { useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router'

import { listArticles } from '../api/articles'
import { listTags } from '../api/users'
import { ArticleCard } from '../components/ArticleCard'
import { primaryButton, secondaryButton } from '../components/buttons'
import { Pagination } from '../components/Pagination'
import { Empty, ErrorState, Loading } from '../components/States'
import { useAuth } from '../auth/context'
import { useAsync } from '../hooks/useAsync'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { signInPath } from '../lib/redirect'

const PAGE_SIZE = 10

/** FE-01: the public catalog with search, popular tags and pagination. */
export function HomePage() {
  useDocumentTitle(null)
  const { user } = useAuth()
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const tag = params.get('tag') ?? ''
  const page = Math.max(1, Number(params.get('page')) || 1)

  const articles = useAsync(`articles?${params.toString()}`, (signal) =>
    listArticles({ q, tag, page, pageSize: PAGE_SIZE }, signal),
  )
  const tags = useAsync('tags', listTags)

  // Typing in the search box does not hit the API; submitting the form does.
  const [draftQuery, setDraftQuery] = useState(q)

  function update(changes: Record<string, string | null>) {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value)
      else next.delete(key)
    }
    if (!('page' in changes)) next.delete('page')
    setParams(next)
  }

  function search(event: FormEvent) {
    event.preventDefault()
    update({ q: draftQuery.trim() || null })
  }

  const popularTags =
    tags.status === 'success'
      ? tags.data
          .filter((t) => t.article_count > 0)
          .sort((a, b) => b.article_count - a.article_count)
      : []

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="font-serif text-3xl font-semibold sm:text-4xl">Essays</h1>
        <Link to={user ? '/write' : signInPath('/write')} className={primaryButton}>
          Write an essay
        </Link>
      </div>

      <form role="search" onSubmit={search} className="mt-6 flex gap-2">
        <label htmlFor="search" className="sr-only">
          Search essays
        </label>
        <input
          id="search"
          type="search"
          value={draftQuery}
          onChange={(e) => setDraftQuery(e.target.value)}
          maxLength={100}
          placeholder="Search titles and summaries"
          className="min-w-0 flex-1 rounded-md border border-rule bg-white px-3 py-2"
        />
        <button type="submit" className={secondaryButton}>
          Search
        </button>
      </form>

      {popularTags.length > 0 && (
        <section aria-labelledby="tags-heading" className="mt-6">
          <h2 id="tags-heading" className="sr-only">
            Popular tags
          </h2>
          <ul className="flex flex-wrap gap-2">
            {popularTags.map((t) => {
              const active = t.slug === tag
              return (
                <li key={t.slug}>
                  <button
                    type="button"
                    aria-pressed={active}
                    onClick={() => update({ tag: active ? null : t.slug })}
                    className={`rounded-full border px-3 py-1 text-sm ${
                      active
                        ? 'border-accent bg-accent text-white'
                        : 'border-rule text-muted hover:border-accent hover:text-accent-strong'
                    }`}
                  >
                    {t.name} <span className="opacity-70">{t.article_count}</span>
                  </button>
                </li>
              )
            })}
          </ul>
        </section>
      )}

      <section aria-label="Articles" className="mt-4">
        {articles.status === 'loading' && <Loading label="Loading essays…" />}
        {articles.status === 'error' && (
          <div className="mt-6">
            <ErrorState error={articles.error} onRetry={articles.reload} />
          </div>
        )}
        {articles.status === 'success' &&
          (articles.data.items.length === 0 ? (
            <div className="mt-6">
              <Empty>
                {q || tag ? (
                  <>
                    No essays match these filters.{' '}
                    <button
                      type="button"
                      className="font-medium text-accent-strong underline"
                      onClick={() => {
                        setDraftQuery('')
                        setParams(new URLSearchParams())
                      }}
                    >
                      Clear filters
                    </button>
                  </>
                ) : (
                  'No essays have been published yet.'
                )}
              </Empty>
            </div>
          ) : (
            <>
              {articles.data.items.map((article) => (
                <ArticleCard key={article.id} article={article} />
              ))}
              <Pagination
                page={page}
                pageSize={PAGE_SIZE}
                total={articles.data.total}
                onChange={(p) => update({ page: String(p) })}
              />
            </>
          ))}
      </section>
    </div>
  )
}
