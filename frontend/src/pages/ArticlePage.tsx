import { Link, useParams } from 'react-router'

import { getArticle } from '../api/articles'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/context'
import { primaryButton } from '../components/buttons'
import { Comments } from '../components/Comments'
import { Markdown } from '../components/Markdown'
import { PostBox } from '../components/PostBox'
import { ReportButton } from '../components/ReportButton'
import { ErrorState, Loading } from '../components/States'
import { TagChips } from '../components/TagChips'
import { BookmarkButton, FollowButton } from '../components/ToggleButtons'
import { useAsync } from '../hooks/useAsync'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { plural } from '../lib/forums'
import { signInPath } from '../lib/redirect'
import { NotFoundPage } from './NotFoundPage'

const statusLabels = { draft: 'Draft', unpublished: 'Unpublished' } as const

/** FE-02 in the Stack Exchange layout: the essay as the question, comments below it. */
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
  const isPublic = data.status === 'published' && data.moderation_status === 'visible'
  return (
    <article className="max-w-[780px]">
      {data.status !== 'published' && (
        <p role="note" className="mb-4 rounded-[5px] border border-note-rule bg-note p-3">
          {statusLabels[data.status]}: only you can see this essay.
        </p>
      )}
      {data.moderation_status === 'hidden' && (
        <p
          role="note"
          className="mb-4 rounded-[5px] border border-red-300 bg-red-50 p-3 text-red-900"
        >
          Hidden by a moderator: readers cannot see this essay.
        </p>
      )}
      <header className="border-b border-rule pb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h1 className="min-w-0 text-[27px] leading-tight break-words">{data.title}</h1>
          <Link to={user ? '/write' : signInPath('/write')} className={primaryButton}>
            Write an essay
          </Link>
        </div>
        {data.summary && <p className="mt-2 text-[15px] text-muted">{data.summary}</p>}
        {isPublic && (
          <p className="mt-2 text-[13px] text-muted">
            {plural(data.comment_count, 'comment', 'comments')} ·{' '}
            {plural(data.bookmark_count, 'save', 'saves')}
          </p>
        )}
      </header>
      <PostBox
        number={1}
        author={data.author}
        byEssayAuthor
        verb="published"
        postedAt={data.published_at}
        footer={
          <>
            {isPublic && (
              <>
                <BookmarkButton articleId={data.id} initial={data.bookmarked_by_me} />
                <FollowButton
                  authorId={data.author.id}
                  authorName={data.author.display_name}
                  initial={data.following_author}
                />
              </>
            )}
            {isAuthor && (
              <Link to={`/write/${data.id}`} className="text-muted hover:text-ink">
                Edit
              </Link>
            )}
            {isPublic && user && !isAuthor && (
              <ReportButton targetType="article" targetId={data.id} />
            )}
          </>
        }
      >
        <Markdown source={data.body_markdown} />
        <div className="mt-6">
          <TagChips tags={data.tags} />
        </div>
      </PostBox>
      {isPublic && <Comments articleId={data.id} essayAuthorId={data.author.id} />}
    </article>
  )
}
