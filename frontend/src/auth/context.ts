import { createContext, useContext } from 'react'

import type { RegisterData } from '../api/auth'
import type { Me } from '../api/types'

export type Auth = {
  /** undefined while the first /auth/me request is running, null for guests. */
  user: Me | null | undefined
  signIn: (email: string, password: string) => Promise<void>
  signUp: (data: RegisterData) => Promise<void>
  /** Ends the session and goes to the home page. */
  signOut: () => Promise<void>
  /** Replace the cached user after a profile or interests change. */
  setUser: (user: Me) => void
}

export const AuthContext = createContext<Auth | null>(null)

export function useAuth(): Auth {
  const auth = useContext(AuthContext)
  if (!auth) throw new Error('useAuth must be used inside <AuthProvider>')
  return auth
}
