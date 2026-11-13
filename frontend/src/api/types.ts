// Mirrors the Pydantic response models in backend/app/schemas.

export type Tag = { slug: string; name: string }
export type TagWithCount = Tag & { article_count: number }

export type AuthorBrief = { id: string; handle: string; display_name: string }

export type Author = AuthorBrief & {
  bio: string
  website: string | null
  created_at: string
}

export type AuthorProfile = Author & { followed_by_me: boolean }

export type Me = Author & {
  email: string
  role: 'user' | 'admin'
  interests: Tag[]
}

export type ArticleStatus = 'draft' | 'published' | 'unpublished'

export type ArticleListItem = {
  id: string
  slug: string
  title: string
  summary: string
  status: ArticleStatus
  author: AuthorBrief
  tags: Tag[]
  published_at: string | null
  updated_at: string
}

export type Article = ArticleListItem & {
  body_markdown: string
  created_at: string
  moderation_status: 'visible' | 'hidden'
}

export type ArticleDetail = Article & { bookmarked_by_me: boolean; following_author: boolean }

export type Comment = {
  id: string
  article_id: string
  author: AuthorBrief
  text: string
  created_at: string
  updated_at: string
}

export type FollowedAuthor = { author: AuthorBrief; created_at: string }

export type Page<T> = {
  items: T[]
  page: number
  page_size: number
  total: number
}

export type Recommendation = { article: ArticleListItem; reason: string; score: number }

export type RecommendationPage = Page<Recommendation> & { cold_start: boolean }
