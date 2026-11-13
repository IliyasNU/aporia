import type { ReactNode } from 'react'
import { Link } from 'react-router'

import type { AuthorBrief } from '../api/types'
import { formatDate } from '../lib/format'
import { Avatar } from './Avatar'

type Props = {
  /** Position in the page: the essay is #1, comments follow. */
  number: number
  author: AuthorBrief
  /** Highlights posts by the essay's author, like the asker's card on Stack Exchange. */
  byEssayAuthor?: boolean
  /** "published" for the essay, "commented" for a comment. */
  verb: string
  postedAt: string | null
  children: ReactNode
  /** Small actions under the text: edit, delete, report. */
  footer?: ReactNode
}

/** One post: the text, then its actions on the left and the author's card on the right. */
export function PostBox({
  number,
  author,
  byEssayAuthor,
  verb,
  postedAt,
  children,
  footer,
}: Props) {
  const anchor = `post-${number}`
  return (
    <article
      id={anchor}
      aria-label={`Post ${number} by ${author.display_name}`}
      className="border-b border-rule py-4"
    >
      {children}
      <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-[13px] text-muted">
          <a
            href={`#${anchor}`}
            aria-label={`Link to post ${number}`}
            className="text-muted hover:text-ink"
          >
            Link
          </a>
          {footer}
        </div>
        <div
          className={`ml-auto w-[200px] rounded-[3px] p-[7px] ${byEssayAuthor ? 'bg-owner' : ''}`}
        >
          <p className="mb-1 text-xs text-muted">
            {postedAt ? (
              <>
                {verb} <time dateTime={postedAt}>{formatDate(postedAt)}</time>
              </>
            ) : (
              'not published yet'
            )}
          </p>
          <div className="flex items-center gap-2">
            <Avatar name={author.display_name} />
            <div className="min-w-0 leading-tight">
              <Link
                to={`/authors/${author.handle}`}
                className="text-[13px] break-words text-accent hover:text-button"
              >
                {author.display_name}
              </Link>
              <p className="text-xs break-all text-muted">
                @{author.handle}
                {byEssayAuthor && <span className="sr-only"> (author of the essay)</span>}
              </p>
            </div>
          </div>
        </div>
      </div>
    </article>
  )
}
