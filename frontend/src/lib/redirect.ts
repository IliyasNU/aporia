/**
 * Only allow redirects to paths on this site after sign-in. "//evil.example"
 * or "https://evil.example" in ?next= would otherwise send users elsewhere.
 */
export function safeNext(next: string | null): string {
  if (!next || !next.startsWith('/') || next.startsWith('//') || hasUnsafeCharacter(next)) {
    return '/'
  }
  return next
}

/**
 * Backslashes, control characters and tabs/newlines (raw or %-encoded) are
 * refused: browsers ignore or reinterpret some of them, which could turn a
 * path into the address of another site.
 */
function hasUnsafeCharacter(path: string): boolean {
  for (const char of path) {
    const code = char.charCodeAt(0)
    if (code < 0x20 || code === 0x7f || char === '\\') return true
  }
  return /%(0[0-9a-f]|1[0-9a-f]|5c|7f)/i.test(path)
}

export function signInPath(next: string): string {
  return `/signin?next=${encodeURIComponent(next)}`
}
