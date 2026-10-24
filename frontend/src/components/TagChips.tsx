import { Link } from 'react-router'

import type { Tag } from '../api/types'

export function TagChips({ tags }: { tags: Tag[] }) {
  if (tags.length === 0) return null
  return (
    <ul className="flex flex-wrap gap-2" aria-label="Tags">
      {tags.map((tag) => (
        <li key={tag.slug}>
          <Link
            to={`/?tag=${tag.slug}`}
            className="rounded-full border border-rule px-2.5 py-0.5 text-sm text-muted hover:border-accent hover:text-accent-strong"
          >
            {tag.name}
          </Link>
        </li>
      ))}
    </ul>
  )
}
