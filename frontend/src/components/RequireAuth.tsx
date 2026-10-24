import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'

import { useAuth } from '../auth/context'
import { signInPath } from '../lib/redirect'
import { Loading } from './States'

/** Shows its children to signed-in users and sends guests to the sign-in page. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const location = useLocation()
  if (user === undefined) return <Loading />
  if (user === null) {
    return <Navigate to={signInPath(location.pathname + location.search)} replace />
  }
  return children
}
