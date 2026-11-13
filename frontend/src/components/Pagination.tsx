type Props = {
  page: number
  pageSize: number
  total: number
  onChange: (page: number) => void
}

export function Pagination({ page, pageSize, total, onChange }: Props) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  if (pages <= 1) return null
  const button =
    'rounded-md border border-rule px-3 py-1.5 hover:border-accent disabled:cursor-not-allowed disabled:opacity-40'
  return (
    <nav aria-label="Pagination" className="mt-8 flex items-center justify-between gap-4">
      <button
        type="button"
        className={button}
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
      >
        ← Newer
      </button>
      <span className="text-sm text-muted">
        Page {page} of {pages}
      </span>
      <button
        type="button"
        className={button}
        disabled={page >= pages}
        onClick={() => onChange(page + 1)}
      >
        Older →
      </button>
    </nav>
  )
}
