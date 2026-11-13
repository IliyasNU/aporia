import { Link, useSearchParams } from 'react-router'

import { followingFeed } from '../api/social'
import { Pagination } from '../components/Pagination'
import { PageTitle, Panel } from '../components/Panel'
import { Empty, ErrorState, Loading } from '../components/States'
import { TopicList } from '../components/TopicList'
import { useAsync } from '../hooks/useAsync'
import { useDocumentTitle } from '../hooks/useDocumentTitle'

/** SOC-01: new essays by the authors you follow. Rendered inside <RequireAuth>. */
export function FollowingPage() {
  useDocumentTitle('Following')
  const [params, setParams] = useSearchParams()
  const page = Math.max(1, Number(params.get('page')) || 1)
  const feed = useAsync(`following:${page}`, (signal) => followingFeed(page, signal))

  return (
    <div className="space-y-6">
      <PageTitle lead="New essays by the authors you follow.">Following</PageTitle>
      <Panel title="From the authors you follow">
        {feed.status === 'loading' && (
          <div className="px-4">
            <Loading label="Loading essays…" />
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
              <TopicList
                label="Essays by the authors you follow"
                topics={feed.data.items.map((article) => ({ article }))}
              />
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
