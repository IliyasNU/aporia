import type { ReactNode } from 'react'
import { Link, NavLink } from 'react-router'

import { useAuth } from '../auth/context'

const navLink = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-2 py-1 hover:text-accent-strong ${isActive ? 'text-accent-strong' : 'text-muted'}`

export function Layout({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:rounded-md focus:bg-white focus:px-3 focus:py-2"
      >
        Skip to content
      </a>
      <header className="border-b border-rule">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-4">
          <Link to="/" className="font-serif text-2xl font-semibold tracking-tight">
            Aporia
          </Link>
          <nav aria-label="Main" className="flex flex-wrap items-center gap-x-2 text-sm">
            <NavLink to="/" end className={navLink}>
              Essays
            </NavLink>
            <NavLink to="/for-you" className={navLink}>
              For you
            </NavLink>
            {user ? (
              <>
                <NavLink to="/following" className={navLink}>
                  Following
                </NavLink>
                <NavLink to="/write" className={navLink}>
                  Write
                </NavLink>
                <NavLink to="/account" className={navLink}>
                  @{user.handle}
                </NavLink>
              </>
            ) : (
              user === null && (
                <>
                  <NavLink to="/signin" className={navLink}>
                    Sign in
                  </NavLink>
                  <NavLink to="/signup" className={navLink}>
                    Sign up
                  </NavLink>
                </>
              )
            )}
          </nav>
        </div>
      </header>

      <main id="main" className="mx-auto w-full max-w-3xl flex-1 px-4 py-8 sm:py-12">
        {children}
      </main>

      <footer className="border-t border-rule">
        <div className="mx-auto flex max-w-3xl flex-wrap justify-between gap-2 px-4 py-6 text-sm text-muted">
          <span>Aporia · a home for philosophical essays</span>
          <nav aria-label="Site information" className="flex gap-4">
            <Link to="/rules" className="hover:text-accent-strong">
              Publication rules
            </Link>
            <Link to="/privacy" className="hover:text-accent-strong">
              Privacy
            </Link>
          </nav>
        </div>
      </footer>
    </div>
  )
}
