// Mirrors the Pydantic response models in backend/app/schemas.

export type Tag = { slug: string; name: string }
export type TagWithCount = Tag & { article_count: number }

export type AuthorBrief = { id: string; handle: string; display_name: string }

export type Author = AuthorBrief & {
  bio: string
  website: string | null
  created_at: string
}

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
}

export type Page<T> = {
  items: T[]
  page: number
  page_size: number
  total: number
}
