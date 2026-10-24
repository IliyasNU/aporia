const dateFormat = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})

export function formatDate(iso: string | null): string {
  return iso ? dateFormat.format(new Date(iso)) : ''
}

/** "Ada Lovelace" -> "AL": the system avatar instead of uploaded pictures. */
export function initials(name: string): string {
  const letters = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word.charAt(0).toUpperCase())
    .join('')
  return letters || '?'
}
