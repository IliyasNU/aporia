import { Link, useSearchParams } from 'react-router'

import { listArticles } from '../api/articles'
import { listTags } from '../api/users'
import { useAuth } from '../auth/context'
import { primaryButton } from '../components/buttons'
import { Pagination } from '../components/Pagination'
import { PageTitle } from '../components/Panel'
import { Empty, ErrorState, Loading } from '../components/States'
import { tagChip } from '../components/TagChips'
import { TopicList } from '../components/TopicList'
import { useAsync } from '../hooks/useAsync'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { forumDescriptions, plural } from '../lib/forums'
import { signInPath } from '../lib/redirect'

const PAGE_SIZE = 10
const SORTS = [
  { value: 'latest', label: 'Latest' },
  { value: 'popular', label: 'Most saved' },
] as const

/**
 * FE-01 in the Stack Exchange layout: the essay list with sort tabs, and a sidebar
 * with the popular tags. ?q= (from the top bar), ?tag=, ?sort= and ?page= live in the URL.
 */
export function HomePage() {
  const { user } = useAuth()
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const tag = params.get('tag') ?? ''
  const sort = params.get('sort') === 'popular' ? 'popular' : 'latest'
  const page = Math.max(1, Number(params.get('page')) || 1)

  const articles = useAsync(`articles?${params.toString()}`, (signal) =>
    listArticles({ q, tag, sort, page, pageSize: PAGE_SIZE }, signal),
  )
  const tags = useAsync('tags', listTags)
  const tagName = (tags.status === 'success' && tags.data.find((t) => t.slug === tag)?.name) || tag
  useDocumentTitle(q ? 'Search' : tag ? tagName : null)

  function update(changes: Record<string, string | null>) {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value)
      else next.delete(key)
    }
    if (!('page' in changes)) next.delete('page')
    setParams(next)
  }

  const popularTags =
    tags.status === 'success'
      ? tags.data
          .filter((t) => t.article_count > 0)
          .sort((a, b) => b.article_count - a.article_count)
      : []

  return (
    <div className="flex flex-col gap-8 lg:flex-row lg:gap-6">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <PageTitle
            lead={
              q
                ? `Essays matching “${q}”${tag ? ` and tagged ${tagName}` : ''}.`
                : tag
                  ? forumDescriptions[tag]
                  : undefined
            }
          >
            {q ? 'Search results' : tag ? `Essays tagged ${tagName}` : 'Essays'}
          </PageTitle>
          <Link to={user ? '/write' : signInPath('/write')} className={primaryButton}>
            Write an essay
          </Link>
        </div>

        <div className="mt-4 mb-3 flex flex-wrap items-center justify-between gap-3">
          <p className="text-[17px]">
            {articles.status === 'success' && plural(articles.data.total, 'essay', 'essays')}
          </p>
          <div role="group" aria-label="Sort by" className="flex">
            {SORTS.map((option, index) => {
              const active = option.value === sort
              return (
                <button
                  key={option.value}
                  type="button"
                  aria-current={active ? 'true' : undefined}
                  onClick={() => update({ sort: option.value === 'popular' ? 'popular' : null })}
                  className={`border border-[#9fa6ad] px-2.5 py-[7px] text-xs leading-none ${
                    index === 0 ? 'rounded-l-[6px]' : '-ml-px rounded-r-[6px]'
                  } ${active ? 'bg-[#e3e6e8] text-ink' : 'bg-white text-muted hover:bg-row'}`}
                >
                  {option.label}
                </button>
              )
            })}
          </div>
        </div>

        <section aria-label="Articles">
          {articles.status === 'loading' && <Loading label="Loading essays…" />}
          {articles.status === 'error' && (
            <ErrorState error={articles.error} onRetry={articles.reload} />
          )}
          {articles.status === 'success' &&
            (articles.data.items.length === 0 ? (
              <Empty>
                {q || tag ? (
                  <>
                    No essays match these filters.{' '}
                    <button
                      type="button"
                      className="text-accent hover:text-button"
                      onClick={() => setParams(new URLSearchParams())}
                    >
                      Clear filters
                    </button>
                  </>
                ) : (
                  'No essays have been published yet.'
                )}
              </Empty>
            ) : (
              <>
                <TopicList
                  label="Essays"
                  topics={articles.data.items.map((article) => ({ article }))}
                />
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

      <aside aria-label="Sidebar" className="w-full shrink-0 space-y-4 lg:w-[300px]">
        <section
          aria-labelledby="welcome-heading"
          className="rounded-[5px] border border-note-rule bg-note text-[#3b4045]"
        >
          <h2
            id="welcome-heading"
            className="border-b border-note-rule bg-[#fbf3d5] px-4 py-3 text-xs font-bold text-[#525960]"
          >
            Welcome to Aporia
          </h2>
          <ul className="space-y-2 px-4 py-3">
            <li>Long-form philosophy, written in Markdown and discussed in the comments.</li>
            <li>Save essays, follow authors, or get their new essays by email.</li>
            <li>
              Please read the{' '}
              <Link to="/rules" className="text-accent hover:text-button">
                publication rules
              </Link>{' '}
              before you write.
            </li>
          </ul>
        </section>

        {popularTags.length > 0 && (
          <section aria-labelledby="tags-heading">
            <h2 id="tags-heading" className="mb-3 text-[19px]">
              Popular tags
            </h2>
            <ul className="flex flex-wrap gap-x-1 gap-y-2">
              {popularTags.map((t) => {
                const active = t.slug === tag
                return (
                  <li key={t.slug}>
                    <button
                      type="button"
                      aria-pressed={active}
                      onClick={() => update({ tag: active ? null : t.slug })}
                      className={`${tagChip} ${active ? 'ring-2 ring-tag-ink' : ''}`}
                    >
                      {t.name} <span className="text-muted">× {t.article_count}</span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </section>
        )}
      </aside>
    </div>
  )
}
