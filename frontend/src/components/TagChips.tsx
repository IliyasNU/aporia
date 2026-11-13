import { Link } from 'react-router'

import type { Tag } from '../api/types'

export const tagChip =
  'inline-block rounded-[4px] bg-tag px-[6px] py-[4.8px] text-xs leading-none text-tag-ink hover:bg-tag-hover hover:text-[#2c5877]'

/** An essay's topics as Stack Exchange tags; each lists the essays with that tag. */
export function TagChips({ tags }: { tags: Tag[] }) {
  if (tags.length === 0) return null
  return (
    <ul className="flex flex-wrap gap-1" aria-label="Tags">
      {tags.map((tag) => (
        <li key={tag.slug}>
          <Link to={`/?tag=${tag.slug}`} className={tagChip}>
            {tag.name}
          </Link>
        </li>
      ))}
    </ul>
  )
}
