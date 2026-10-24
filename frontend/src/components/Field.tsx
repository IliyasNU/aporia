import { useId, type InputHTMLAttributes, type TextareaHTMLAttributes } from 'react'

const control =
  'mt-1 block w-full rounded-md border border-rule bg-white px-3 py-2 text-base text-ink shadow-xs focus:border-accent'

type Common = { label: string; error?: string; hint?: string }

function Messages({ id, error, hint }: { id: string; error?: string; hint?: string }) {
  return (
    <>
      {hint && !error && (
        <p id={`${id}-hint`} className="mt-1 text-sm text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="mt-1 text-sm text-red-800">
          {error}
        </p>
      )}
    </>
  )
}

function describedBy(id: string, error?: string, hint?: string) {
  if (error) return `${id}-error`
  if (hint) return `${id}-hint`
  return undefined
}

export function TextField({
  label,
  error,
  hint,
  ...input
}: Common & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId()
  return (
    <div>
      <label htmlFor={id} className="block font-medium">
        {label}
      </label>
      <input
        id={id}
        className={control}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(id, error, hint)}
        {...input}
      />
      <Messages id={id} error={error} hint={hint} />
    </div>
  )
}

export function TextArea({
  label,
  error,
  hint,
  ...textarea
}: Common & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const id = useId()
  return (
    <div>
      <label htmlFor={id} className="block font-medium">
        {label}
      </label>
      <textarea
        id={id}
        className={control}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(id, error, hint)}
        {...textarea}
      />
      <Messages id={id} error={error} hint={hint} />
    </div>
  )
}
