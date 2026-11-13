import { Link, useParams, useSearchParams } from 'react-router'

import { listArticles } from '../api/articles'
import { ApiError } from '../api/client'
import { getAuthor } from '../api/users'
import { useAuth } from '../auth/context'
import { Avatar } from '../components/Avatar'
import { NewsletterForm } from '../components/NewsletterForm'
import { Pagination } from '../components/Pagination'
import { Panel } from '../components/Panel'
import { Empty, ErrorState, Loading } from '../components/States'
import { FollowButton } from '../components/ToggleButtons'
import { TopicList } from '../components/TopicList'
import { useAsync } from '../hooks/useAsync'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { formatDate } from '../lib/format'
import { NotFoundPage } from './NotFoundPage'

const PAGE_SIZE = 10

/** FE-03, as a forum member profile: who they are, email updates, the essays they started. */
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
  const isSelf = user?.id === profile.id
  return (
    <div className="space-y-6">
      <div>
        <header className="flex flex-wrap items-start gap-4">
          <Avatar name={profile.display_name} size="lg" />
          <div className="min-w-0 flex-1">
            <h1 className="text-[34px] leading-tight break-words">{profile.display_name}</h1>
            <p className="mt-1 text-[13px] text-muted">
              @{profile.handle} · Member since {formatDate(profile.created_at)}
            </p>
            {profile.bio && (
              <p className="mt-3 max-w-[65ch] text-[15px] whitespace-pre-line">{profile.bio}</p>
            )}
            {profile.website && (
              <p className="mt-2">
                <a
                  href={profile.website}
                  rel="nofollow ugc noopener noreferrer"
                  className="break-all text-accent hover:text-button"
                >
                  {profile.website}
                </a>
              </p>
            )}
            {isSelf ? (
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
      </div>

      {!isSelf && <NewsletterForm authorId={profile.id} authorName={profile.display_name} />}

      <Panel title={`Essays by ${profile.display_name}`}>
        {articles.status === 'loading' && (
          <div className="px-4">
            <Loading label="Loading essays…" />
          </div>
        )}
        {articles.status === 'error' && (
          <div className="p-4">
            <ErrorState error={articles.error} onRetry={articles.reload} />
          </div>
        )}
        {articles.status === 'success' &&
          (articles.data.items.length === 0 ? (
            <div className="p-4">
              <Empty>{profile.display_name} has not published any essays yet.</Empty>
            </div>
          ) : (
            <>
              <TopicList
                label={`Essays by ${profile.display_name}`}
                topics={articles.data.items.map((article) => ({ article }))}
              />
              <Pagination
                page={page}
                pageSize={PAGE_SIZE}
                total={articles.data.total}
                onChange={(p) => setParams({ page: String(p) })}
              />
            </>
          ))}
      </Panel>
    </div>
  )
}
