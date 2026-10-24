/**
 * Only allow redirects to paths on this site after sign-in. "//evil.example"
 * or "https://evil.example" in ?next= would otherwise send users elsewhere.
 */
export function safeNext(next: string | null): string {
  if (!next || !next.startsWith('/') || next.startsWith('//') || next.startsWith('/\\')) {
    return '/'
  }
  return next
}

export function signInPath(next: string): string {
  return `/signin?next=${encodeURIComponent(next)}`
}
