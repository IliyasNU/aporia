import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

// findBy*/waitFor give up after 1 s by default. A full run on a busy CI machine
// can be slower than that for multi-request pages, so allow up to 5 s.
configure({ asyncUtilTimeout: 5000 })

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})
