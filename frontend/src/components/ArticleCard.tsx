import { Link } from 'react-router'

import type { ArticleListItem } from '../api/types'
import { formatDate } from '../lib/format'
import { TagChips } from './TagChips'

export function ArticleCard({ article }: { article: ArticleListItem }) {
  return (
    <article className="border-b border-rule py-6">
      <h2 className="font-serif text-2xl leading-snug font-semibold">
        <Link
          to={`/articles/${encodeURIComponent(article.slug)}`}
          className="hover:text-accent-strong"
        >
          {article.title}
        </Link>
      </h2>
      {article.summary && (
        <p className="mt-2 text-lg leading-relaxed text-muted">{article.summary}</p>
      )}
      <p className="mt-3 text-sm text-muted">
        <Link
          to={`/authors/${article.author.handle}`}
          className="font-medium text-ink hover:underline"
        >
          {article.author.display_name}
        </Link>
        {article.published_at && (
          <>
            {' · '}
            <time dateTime={article.published_at}>{formatDate(article.published_at)}</time>
          </>
        )}
      </p>
      <div className="mt-3">
        <TagChips tags={article.tags} />
      </div>
    </article>
  )
}
