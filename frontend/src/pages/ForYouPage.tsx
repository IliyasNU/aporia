import { Link, useSearchParams } from 'react-router'

import { recommendedFeed } from '../api/social'
import { useAuth } from '../auth/context'
import { ArticleCard } from '../components/ArticleCard'
import { Pagination } from '../components/Pagination'
import { Empty, ErrorState, Loading } from '../components/States'
import { useAsync } from '../hooks/useAsync'
import { useDocumentTitle } from '../hooks/useDocumentTitle'

/** FE-06: recommendations, each with the reason it was picked. Works for guests too. */
export function ForYouPage() {
  useDocumentTitle('For you')
  const { user } = useAuth()
  const [params, setParams] = useSearchParams()
  const page = Math.max(1, Number(params.get('page')) || 1)
  const feed = useAsync(`for-you:${user?.id ?? 'guest'}:${page}`, (signal) =>
    recommendedFeed(page, signal),
  )

  return (
    <div>
      <h1 className="font-serif text-3xl font-semibold sm:text-4xl">For you</h1>
      <p className="mt-2 text-muted">
        Picked from your interests, the authors you follow, what readers save and what is new. Every
        essay says why it is here.
      </p>

      {feed.status === 'success' && feed.data.cold_start && (
        <p role="note" className="mt-4 rounded-md border border-rule bg-white p-3 text-sm">
          {user ? (
            <>
              These are new and popular essays.{' '}
              <Link to="/account" className="font-medium text-accent-strong underline">
                Choose your interests
              </Link>{' '}
              or follow authors to make this list your own.
            </>
          ) : (
            <>
              These are new and popular essays.{' '}
              <Link
                to="/signin?next=%2Ffor-you"
                className="font-medium text-accent-strong underline"
              >
                Sign in
              </Link>{' '}
              and choose your interests for a personal selection.
            </>
          )}
        </p>
      )}

      {feed.status === 'loading' && <Loading label="Finding essays for you…" />}
      {feed.status === 'error' && (
        <div className="mt-6">
          <ErrorState error={feed.error} onRetry={feed.reload} />
        </div>
      )}
      {feed.status === 'success' &&
        (feed.data.items.length === 0 ? (
          <div className="mt-6">
            <Empty>No essays to recommend yet. Check back after authors publish.</Empty>
          </div>
        ) : (
          <>
            {feed.data.items.map(({ article, reason }) => (
              <ArticleCard key={article.id} article={article} reason={reason} />
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
