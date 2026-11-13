import { Link } from 'react-router'

import type { ArticleListItem } from '../api/types'
import { formatDate } from '../lib/format'
import { Avatar } from './Avatar'
import { TagChips } from './TagChips'

export type Topic = { article: ArticleListItem; reason?: string }

/** Essays as Stack Exchange question summaries: counts on the left, title and tags on the right. */
export function TopicList({ topics, label }: { topics: Topic[]; label: string }) {
  return (
    <ol aria-label={label} className="border-t border-rule">
      {topics.map((topic) => (
        <TopicRow key={topic.article.id} {...topic} />
      ))}
    </ol>
  )
}

function TopicRow({ article, reason }: Topic) {
  const comments = article.comment_count
  return (
    <li className="flex flex-col gap-2 border-b border-rule p-4 sm:flex-row sm:gap-4">
      <div className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-muted sm:w-[108px] sm:flex-col sm:items-end">
        <Count value={article.bookmark_count} one="save" many="saves" />
        <span
          className={
            comments > 0 ? 'rounded-[3px] border border-success px-1 text-success' : undefined
          }
        >
          <Count value={comments} one="comment" many="comments" />
        </span>
      </div>
      <div className="min-w-0 flex-1">
        {reason && (
          <p className="mb-1 text-xs text-[#a35200]">
            <span className="sr-only">Why this essay: </span>
            {reason}
          </p>
        )}
        <h3 className="text-[17px] leading-snug break-words">
          <Link
            to={`/articles/${encodeURIComponent(article.slug)}`}
            className="text-accent hover:text-button"
          >
            {article.title}
          </Link>
        </h3>
        {article.summary && (
          <p className="mt-1 line-clamp-2 text-[13px] text-[#3b4045]">{article.summary}</p>
        )}
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
          <TagChips tags={article.tags} />
          <p className="ml-auto flex items-center gap-1 text-xs text-muted">
            <Avatar name={article.author.display_name} size="xs" />
            <Link
              to={`/authors/${article.author.handle}`}
              className="text-accent hover:text-button"
            >
              {article.author.display_name}
            </Link>
            {article.published_at && (
              <>
                {' '}
                published{' '}
                <time dateTime={article.published_at}>{formatDate(article.published_at)}</time>
              </>
            )}
          </p>
        </div>
      </div>
    </li>
  )
}

function Count({ value, one, many }: { value: number; one: string; many: string }) {
  return (
    <span className="whitespace-nowrap">
      <b className="font-semibold text-ink">{value}</b> {value === 1 ? one : many}
    </span>
  )
}
