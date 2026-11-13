import { initials } from '../lib/format'

const sizes = {
  xs: 'size-4 rounded-[3px] text-[8px]',
  sm: 'size-8 rounded-[4px] text-xs',
  md: 'size-12 rounded-[5px] text-base',
  lg: 'size-32 rounded-[6px] text-4xl',
} as const

// Like Stack Exchange's generated avatars: a steady colour per name.
// Classes, not inline styles: the Content-Security-Policy allows only our stylesheet.
const colours = [
  'bg-[#5b8db8]',
  'bg-[#5f8f4c]',
  'bg-[#a86b3c]',
  'bg-[#8a6bb1]',
  'bg-[#36878a]',
  'bg-[#b0566d]',
  'bg-[#6b7682]',
]

function colourFor(name: string): string {
  let hash = 0
  for (const char of name) hash = (hash * 31 + char.charCodeAt(0)) >>> 0
  return colours[hash % colours.length] ?? 'bg-[#6b7682]'
}

/** System avatar: the author's initials (no uploaded pictures in v1.0). */
export function Avatar({ name, size = 'sm' }: { name: string; size?: keyof typeof sizes }) {
  return (
    <span
      aria-hidden="true"
      className={`inline-flex shrink-0 items-center justify-center font-semibold text-white ${colourFor(name)} ${sizes[size]}`}
    >
      {initials(name)}
    </span>
  )
}
