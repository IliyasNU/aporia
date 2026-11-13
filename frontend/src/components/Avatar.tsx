import { initials } from '../lib/format'

const sizes = { sm: 'size-8 text-xs', lg: 'size-16 text-xl' } as const

/** System avatar: the author's initials (no uploaded pictures in v1.0). */
export function Avatar({ name, size = 'sm' }: { name: string; size?: keyof typeof sizes }) {
  return (
    <span
      aria-hidden="true"
      className={`inline-flex shrink-0 items-center justify-center rounded-full bg-accent/10 font-semibold text-accent-strong ${sizes[size]}`}
    >
      {initials(name)}
    </span>
  )
}
