import { useEffect, useState } from 'react'

export type AsyncState<T> =
  { status: 'loading' } | { status: 'success'; data: T } | { status: 'error'; error: unknown }

type Settled<T> = { key: string; version: number; state: AsyncState<T> }

/**
 * Runs `load` whenever `key` changes and tracks loading / success / error.
 *
 * `key` must change whenever the request changes (e.g. include the query
 * string). Older responses are discarded, so fast typing or paging never shows
 * stale results. `reload()` fetches again but keeps showing the current data
 * until the new data arrives, so lists do not flicker after an edit.
 */
export function useAsync<T>(
  key: string,
  load: (signal: AbortSignal) => Promise<T>,
): AsyncState<T> & { reload: () => void } {
  const [version, setVersion] = useState(0)
  const [settled, setSettled] = useState<Settled<T> | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    load(controller.signal).then(
      (data) => setSettled({ key, version, state: { status: 'success', data } }),
      (error: unknown) => {
        if (!controller.signal.aborted) {
          setSettled({ key, version, state: { status: 'error', error } })
        }
      },
    )
    return () => controller.abort()
    // `load` is recreated on every render; `key` and `version` identify the request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, version])

  let state: AsyncState<T> = { status: 'loading' }
  if (settled?.key === key) {
    const current = settled.version === version
    if (current || settled.state.status === 'success') state = settled.state
  }
  return { ...state, reload: () => setVersion((v) => v + 1) }
}
