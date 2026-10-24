import { useEffect, useState } from 'react'

export type AsyncState<T> =
  { status: 'loading' } | { status: 'success'; data: T } | { status: 'error'; error: unknown }

/**
 * Runs `load` whenever `key` changes and tracks loading / success / error.
 *
 * `key` must change whenever the request changes (e.g. include the query
 * string). Older responses are discarded, so fast typing or paging never shows
 * stale results.
 */
export function useAsync<T>(
  key: string,
  load: (signal: AbortSignal) => Promise<T>,
): AsyncState<T> & { reload: () => void } {
  const [version, setVersion] = useState(0)
  const [settled, setSettled] = useState<{ key: string; state: AsyncState<T> } | null>(null)
  const requestKey = `${key}#${version}`

  useEffect(() => {
    const controller = new AbortController()
    load(controller.signal).then(
      (data) => setSettled({ key: requestKey, state: { status: 'success', data } }),
      (error: unknown) => {
        if (!controller.signal.aborted) {
          setSettled({ key: requestKey, state: { status: 'error', error } })
        }
      },
    )
    return () => controller.abort()
    // `load` is recreated on every render; `requestKey` identifies the request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestKey])

  const state: AsyncState<T> = settled?.key === requestKey ? settled.state : { status: 'loading' }
  return { ...state, reload: () => setVersion((v) => v + 1) }
}
