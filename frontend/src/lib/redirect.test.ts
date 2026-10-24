import { describe, expect, it } from 'vitest'

import { safeNext } from './redirect'

describe('safeNext', () => {
  it.each([
    ['/write', '/write'],
    ['/articles/on-doubt?x=1', '/articles/on-doubt?x=1'],
    [null, '/'],
    ['', '/'],
    ['https://evil.example', '/'],
    ['//evil.example', '/'],
    ['/\\evil.example', '/'],
    ['javascript:alert(1)', '/'],
  ])('%s -> %s', (next, expected) => {
    expect(safeNext(next)).toBe(expected)
  })
})
