import { useId, type ReactNode } from 'react'

type Props = {
  title: ReactNode
  /** Buttons or links at the right of the heading. */
  actions?: ReactNode
  children: ReactNode
  className?: string
}

/** A titled section with a bordered white box, as on Stack Exchange profile pages. */
export function Panel({ title, actions, children, className = '' }: Props) {
  const id = useId()
  return (
    <section aria-labelledby={id} className={className}>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h2 id={id} className="text-[19px] leading-tight">
          {title}
        </h2>
        {actions}
      </div>
      <div className="overflow-hidden rounded-[5px] border border-rule bg-white [&>nav]:mb-4 [&>nav]:px-4 [&>ol]:border-t-0 [&>ol>li:last-child]:border-b-0">
        {children}
      </div>
    </section>
  )
}

/** The heading every page starts with. */
export function PageTitle({ children, lead }: { children: ReactNode; lead?: ReactNode }) {
  return (
    <div className="min-w-0">
      <h1 className="text-[27px] leading-tight">{children}</h1>
      {lead && <p className="mt-2 max-w-[65ch] text-[15px] text-muted">{lead}</p>}
    </div>
  )
}
