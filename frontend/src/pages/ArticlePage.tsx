import { Link, useParams } from 'react-router'

import { getArticle } from '../api/articles'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/context'
import { Avatar } from '../components/Avatar'
import { Markdown } from '../components/Markdown'
import { ErrorState, Loading } from '../components/States'
import { TagChips } from '../components/TagChips'
import { useAsync } from '../hooks/useAsync'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { formatDate } from '../lib/format'
import { NotFoundPage } from './NotFoundPage'

const statusLabels = { draft: 'Draft', unpublished: 'Unpublished' } as const

/** FE-02: one essay, rendered from Markdown. */
export function ArticlePage() {
  const { slug = '' } = useParams()
  const { user } = useAuth()
  // Re-fetch when the user signs in or out: authors may see their own drafts.
  const article = useAsync(`article:${slug}:${user?.id ?? 'guest'}`, (signal) =>
    getArticle(slug, signal),
  )
  useDocumentTitle(
    article.status === 'success' ? article.data.title : null,
    article.status === 'success' ? article.data.summary : undefined,
  )

  if (article.status === 'loading') return <Loading />
  if (article.status === 'error') {
    if (article.error instanceof ApiError && article.error.status === 404) {
      return <NotFoundPage what="essay" />
    }
    return <ErrorState error={article.error} onRetry={article.reload} />
  }

  const data = article.data
  const isAuthor = user?.id === data.author.id
  return (
    <article>
      {data.status !== 'published' && (
        <p
          role="note"
          className="mb-6 rounded-md border border-amber-300 bg-amber-50 p-3 text-amber-900"
        >
          {statusLabels[data.status]}: only you can see this essay.
        </p>
      )}
      <header>
        <h1 className="font-serif text-3xl leading-tight font-semibold sm:text-5xl">
          {data.title}
        </h1>
        {data.summary && <p className="mt-4 text-xl leading-relaxed text-muted">{data.summary}</p>}
        <div className="mt-6 flex flex-wrap items-center gap-3 text-sm">
          <Avatar name={data.author.display_name} />
          <Link to={`/authors/${data.author.handle}`} className="font-medium hover:underline">
            {data.author.display_name}
          </Link>
          {data.published_at && (
            <time dateTime={data.published_at} className="text-muted">
              {formatDate(data.published_at)}
            </time>
          )}
          {isAuthor && (
            <Link to={`/write/${data.id}`} className="font-medium text-accent-strong underline">
              Edit
            </Link>
          )}
        </div>
        <div className="mt-4">
          <TagChips tags={data.tags} />
        </div>
      </header>
      <div className="mt-10 border-t border-rule pt-8">
        <Markdown source={data.body_markdown} />
      </div>
    </article>
  )
}
