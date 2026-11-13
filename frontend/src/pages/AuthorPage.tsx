import { Link, useParams, useSearchParams } from 'react-router'

import { listArticles } from '../api/articles'
import { ApiError } from '../api/client'
import { getAuthor } from '../api/users'
import { useAuth } from '../auth/context'
import { ArticleCard } from '../components/ArticleCard'
import { Avatar } from '../components/Avatar'
import { Pagination } from '../components/Pagination'
import { NewsletterForm } from '../components/NewsletterForm'
import { Empty, ErrorState, Loading } from '../components/States'
import { FollowButton } from '../components/ToggleButtons'
import { useAsync } from '../hooks/useAsync'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { formatDate } from '../lib/format'
import { NotFoundPage } from './NotFoundPage'

const PAGE_SIZE = 10

/** FE-03: an author's public profile and published essays. */
export function AuthorPage() {
  const { handle = '' } = useParams()
  const { user } = useAuth()
  const [params, setParams] = useSearchParams()
  const page = Math.max(1, Number(params.get('page')) || 1)

  const author = useAsync(`author:${handle}:${user?.id ?? 'guest'}`, (signal) =>
    getAuthor(handle, signal),
  )
  const articles = useAsync(`author-articles:${handle}:${page}`, (signal) =>
    listArticles({ author: handle, page, pageSize: PAGE_SIZE }, signal),
  )
  useDocumentTitle(
    author.status === 'success' ? author.data.display_name : null,
    author.status === 'success' ? author.data.bio : undefined,
  )

  if (author.status === 'loading') return <Loading />
  if (author.status === 'error') {
    if (author.error instanceof ApiError && author.error.status === 404) {
      return <NotFoundPage what="author" />
    }
    return <ErrorState error={author.error} onRetry={author.reload} />
  }

  const profile = author.data
  return (
    <div>
      <header className="flex flex-wrap items-start gap-4">
        <Avatar name={profile.display_name} size="lg" />
        <div className="min-w-0 flex-1">
          <h1 className="font-serif text-3xl font-semibold">{profile.display_name}</h1>
          <p className="text-muted">
            @{profile.handle} · writing since {formatDate(profile.created_at)}
          </p>
          {profile.bio && <p className="mt-3 whitespace-pre-line">{profile.bio}</p>}
          {profile.website && (
            <p className="mt-2">
              <a
                href={profile.website}
                rel="nofollow ugc noopener noreferrer"
                className="break-all text-accent-strong underline"
              >
                {profile.website}
              </a>
            </p>
          )}
          {user?.id === profile.id ? (
            <p className="mt-3">
              <Link to="/account" className="font-medium text-accent-strong underline">
                Edit your profile
              </Link>
            </p>
          ) : (
            <div className="mt-4">
              <FollowButton
                authorId={profile.id}
                authorName={profile.display_name}
                initial={profile.followed_by_me}
              />
            </div>
          )}
        </div>
      </header>

      {user?.id !== profile.id && (
        <div className="mt-8">
          <NewsletterForm authorId={profile.id} authorName={profile.display_name} />
        </div>
      )}

      <section aria-labelledby="essays-heading" className="mt-10">
        <h2
          id="essays-heading"
          className="border-b border-rule pb-2 text-sm font-semibold tracking-wide uppercase"
        >
          Essays
        </h2>
        {articles.status === 'loading' && <Loading label="Loading essays…" />}
        {articles.status === 'error' && (
          <div className="mt-4">
            <ErrorState error={articles.error} onRetry={articles.reload} />
          </div>
        )}
        {articles.status === 'success' &&
          (articles.data.items.length === 0 ? (
            <div className="mt-4">
              <Empty>{profile.display_name} has not published any essays yet.</Empty>
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
                onChange={(p) => setParams({ page: String(p) })}
              />
            </>
          ))}
      </section>
    </div>
  )
}
