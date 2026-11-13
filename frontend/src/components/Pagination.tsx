type Props = {
  page: number
  pageSize: number
  total: number
  onChange: (page: number) => void
}

/** Newer / older pages under a list (hidden when one page is enough). */
export function Pagination({ page, pageSize, total, onChange }: Props) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  if (pages <= 1) return null
  const button =
    'rounded-[3px] border border-rule bg-white px-2 py-1 text-[13px] text-[#3b4045] hover:bg-hover disabled:cursor-not-allowed disabled:opacity-40'
  return (
    <nav aria-label="Pagination" className="mt-6 flex items-center gap-2 px-1">
      <button
        type="button"
        className={button}
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
      >
        ← Newer
      </button>
      <span className="rounded-[3px] bg-orange px-2 py-1 text-[13px] text-white">
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
