import { useState, type ReactNode } from 'react'
import { Link, NavLink, useLocation, useNavigate, useSearchParams } from 'react-router'

import { useAuth } from '../auth/context'
import { Avatar } from './Avatar'
import { primaryButton, secondaryButton } from './buttons'

// Left navigation, Stack Exchange style: the current page is bold with an orange edge.
const navItem = ({ isActive }: { isActive: boolean }) =>
  `block whitespace-nowrap px-3 py-1.5 md:py-2 md:pl-2 ${
    isActive
      ? 'bg-hover font-bold text-ink md:border-r-[3px] md:border-orange'
      : 'text-muted hover:text-ink'
  }`

export function Layout({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const { pathname } = useLocation()
  const [params] = useSearchParams()
  const query = pathname === '/' ? (params.get('q') ?? '') : ''

  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-30 focus:rounded-md focus:bg-white focus:px-3 focus:py-2"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-20 border-t-[3px] border-orange bg-row shadow-[0_1px_2px_hsla(0,0%,0%,0.05),0_1px_4px_hsla(0,0%,0%,0.05),0_2px_8px_hsla(0,0%,0%,0.05)]">
        <div className="mx-auto flex max-w-[1264px] flex-wrap items-center gap-x-3 gap-y-2 px-3 py-2 md:h-[47px] md:flex-nowrap md:py-0">
          <Link to="/" className="flex shrink-0 items-center gap-1.5 px-2 py-1.5 hover:bg-hover">
            <LogoMark />
            <span className="text-[19px] leading-none tracking-tight text-ink">
              apo<b>ria</b>
            </span>
          </Link>
          <SearchForm key={query} initial={query} />
          <div className="ml-auto flex shrink-0 items-center gap-1 md:ml-0">
            {user ? (
              <Link
                to="/account"
                className="flex items-center gap-1.5 px-2 py-1.5 text-ink hover:bg-hover"
              >
                <Avatar name={user.display_name} />
                <span>@{user.handle}</span>
              </Link>
            ) : (
              user === null && (
                <>
                  <Link to="/signin" className={secondaryButton}>
                    Sign in
                  </Link>
                  <Link to="/signup" className={primaryButton}>
                    Sign up
                  </Link>
                </>
              )
            )}
          </div>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-[1264px] flex-1 flex-col md:flex-row">
        <nav
          aria-label="Main"
          className="border-b border-rule md:w-[164px] md:shrink-0 md:border-r md:border-b-0"
        >
          <ul className="flex overflow-x-auto px-1 md:sticky md:top-[50px] md:flex-col md:px-0 md:pt-6">
            <li>
              <NavLink to="/" end className={navItem}>
                Essays
              </NavLink>
            </li>
            <li>
              <NavLink to="/for-you" className={navItem}>
                For you
              </NavLink>
            </li>
            {user && (
              <>
                <li>
                  <NavLink to="/following" className={navItem}>
                    Following
                  </NavLink>
                </li>
                <li>
                  <NavLink to="/write" end className={navItem}>
                    Write
                  </NavLink>
                </li>
              </>
            )}
          </ul>
        </nav>
        <main id="main" className="min-w-0 flex-1 px-4 py-6 md:px-6">
          {children}
        </main>
      </div>

      <footer className="bg-[#232629] text-[#babfc4]">
        <div className="mx-auto flex max-w-[1264px] flex-wrap items-center justify-between gap-3 px-4 py-8 text-[13px]">
          <span className="flex items-center gap-2">
            <LogoMark />
            <span>
              <b className="text-white">Aporia</b> · questions worth thinking about
            </span>
          </span>
          <nav aria-label="Site information" className="flex gap-4">
            <Link to="/rules" className="hover:text-white focus-visible:outline-white">
              Publication rules
            </Link>
            <Link to="/privacy" className="hover:text-white focus-visible:outline-white">
              Privacy
            </Link>
          </nav>
        </div>
      </footer>
    </div>
  )
}

/** The search box in the top bar; it searches the essay list on the home page. */
function SearchForm({ initial }: { initial: string }) {
  const navigate = useNavigate()
  const [draft, setDraft] = useState(initial)
  return (
    <form
      role="search"
      className="relative order-last w-full md:order-none md:w-auto md:flex-1"
      onSubmit={(event) => {
        event.preventDefault()
        const q = draft.trim()
        navigate(q ? `/?q=${encodeURIComponent(q)}` : '/')
      }}
    >
      <label htmlFor="search" className="sr-only">
        Search essays
      </label>
      <svg
        aria-hidden="true"
        viewBox="0 0 18 18"
        className="pointer-events-none absolute top-1/2 left-2.5 size-[18px] -translate-y-1/2 fill-[#838c95]"
      >
        <path d="m18 16.5-5.14-5.18h-.35a7 7 0 1 0-1.19 1.19v.35L16.5 18zM12 7A5 5 0 1 1 2 7a5 5 0 0 1 10 0" />
      </svg>
      <input
        id="search"
        type="search"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        maxLength={100}
        placeholder="Search…"
        className="w-full rounded-[6px] border border-[#babfc4] bg-white py-[7px] pr-2 pl-8 text-[13px] focus:border-[#59a4de] focus:shadow-[0_0_0_4px_hsla(206,100%,40%,0.15)] focus:outline-none"
      />
      <button
        type="submit"
        className="sr-only focus:not-sr-only focus:absolute focus:top-1 focus:right-1"
      >
        Search
      </button>
    </form>
  )
}

/** Aporia's mark: a stack of thoughts ending in an orange question. */
function LogoMark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="size-6">
      <rect x="3" y="15" width="14" height="2.5" rx="1" fill="#bcbbbb" />
      <rect
        x="3"
        y="11"
        width="14"
        height="2.5"
        rx="1"
        fill="#bcbbbb"
        transform="rotate(-6 10 12)"
      />
      <rect
        x="4"
        y="7"
        width="14"
        height="2.5"
        rx="1"
        fill="#f48225"
        transform="rotate(-14 11 8)"
      />
      <path d="M2 19h16v3H2z" fill="#bcbbbb" />
    </svg>
  )
}
