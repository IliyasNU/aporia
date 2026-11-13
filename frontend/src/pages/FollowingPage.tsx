import { Link, useSearchParams } from 'react-router'

import { followingFeed } from '../api/social'
import { ArticleCard } from '../components/ArticleCard'
import { Pagination } from '../components/Pagination'
import { Empty, ErrorState, Loading } from '../components/States'
import { useAsync } from '../hooks/useAsync'
import { useDocumentTitle } from '../hooks/useDocumentTitle'

/** SOC-01: new essays by the authors you follow. Rendered inside <RequireAuth>. */
export function FollowingPage() {
  useDocumentTitle('Following')
  const [params, setParams] = useSearchParams()
  const page = Math.max(1, Number(params.get('page')) || 1)
  const feed = useAsync(`following:${page}`, (signal) => followingFeed(page, signal))

  return (
    <div>
      <h1 className="font-serif text-3xl font-semibold sm:text-4xl">Following</h1>
      <p className="mt-2 text-muted">New essays by the authors you follow.</p>
      {feed.status === 'loading' && <Loading label="Loading essays…" />}
      {feed.status === 'error' && (
        <div className="mt-6">
          <ErrorState error={feed.error} onRetry={feed.reload} />
        </div>
      )}
      {feed.status === 'success' &&
        (feed.data.items.length === 0 ? (
          <div className="mt-6">
            <Empty>
              Nothing here yet. Follow authors from their essays or profiles, or{' '}
              <Link to="/" className="font-medium text-accent-strong underline">
                browse all essays
              </Link>
              .
            </Empty>
          </div>
        ) : (
          <>
            {feed.data.items.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
            <Pagination
              page={page}
              pageSize={10}
              total={feed.data.total}
              onChange={(p) => setParams({ page: String(p) })}
            />
          </>
        ))}
    </div>
  )
}
