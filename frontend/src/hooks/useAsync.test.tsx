import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { useAsync } from './useAsync'

describe('useAsync', () => {
  it('keeps the current data while reloading, then shows the new data', async () => {
    let answer = 'first'
    let release: () => void = () => {}
    const { result } = renderHook(() =>
      useAsync('key', () =>
        answer === 'first'
          ? Promise.resolve(answer)
          : new Promise<string>((resolve) => (release = () => resolve(answer))),
      ),
    )
    await waitFor(() => expect(result.current).toMatchObject({ data: 'first' }))

    answer = 'second'
    act(() => result.current.reload())
    expect(result.current).toMatchObject({ status: 'success', data: 'first' })

    act(() => release())
    await waitFor(() => expect(result.current).toMatchObject({ data: 'second' }))
  })

  it('shows loading again when the key changes', async () => {
    const { result, rerender } = renderHook(({ k }) => useAsync(k, async () => k), {
      initialProps: { k: 'a' },
    })
    await waitFor(() => expect(result.current).toMatchObject({ data: 'a' }))

    rerender({ k: 'b' })

    expect(result.current.status).toBe('loading')
    await waitFor(() => expect(result.current).toMatchObject({ data: 'b' }))
  })
})
