import { Link, useSearchParams } from 'react-router'

import { recommendedFeed } from '../api/social'
import { useAuth } from '../auth/context'
import { Pagination } from '../components/Pagination'
import { PageTitle, Panel } from '../components/Panel'
import { Empty, ErrorState, Loading } from '../components/States'
import { TopicList } from '../components/TopicList'
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
    <div className="space-y-6">
      <PageTitle lead="Picked from your interests, the authors you follow, what readers save and what is new. Every essay says why it is here.">
        For you
      </PageTitle>

      {feed.status === 'success' && feed.data.cold_start && (
        <p role="note" className="rounded-md border border-rule bg-white p-3 text-sm">
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

      <Panel title="Recommended essays">
        {feed.status === 'loading' && (
          <div className="px-4">
            <Loading label="Finding essays for you…" />
          </div>
        )}
        {feed.status === 'error' && (
          <div className="p-4">
            <ErrorState error={feed.error} onRetry={feed.reload} />
          </div>
        )}
        {feed.status === 'success' &&
          (feed.data.items.length === 0 ? (
            <div className="p-4">
              <Empty>No essays to recommend yet. Check back after authors publish.</Empty>
            </div>
          ) : (
            <>
              <TopicList label="Recommended essays" topics={feed.data.items} />
              <Pagination
                page={page}
                pageSize={10}
                total={feed.data.total}
                onChange={(p) => setParams({ page: String(p) })}
              />
            </>
          ))}
      </Panel>
    </div>
  )
}
