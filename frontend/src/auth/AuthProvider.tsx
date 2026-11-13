import { startTransition, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router'

import { fetchMe, login, logout, register, type RegisterData } from '../api/auth'
import type { Me } from '../api/types'
import { AuthContext, type Auth } from './context'

/** Loads the signed-in user once and shares it with the whole app. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null | undefined>(undefined)
  const navigate = useNavigate()

  useEffect(() => {
    const controller = new AbortController()
    fetchMe(controller.signal)
      .then(setUser)
      .catch(() => {
        // The API is unreachable: behave as a guest; pages show their own errors.
        if (!controller.signal.aborted) setUser(null)
      })
    return () => controller.abort()
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    setUser(await login(email, password))
  }, [])

  const signUp = useCallback(async (data: RegisterData) => {
    setUser(await register(data))
  }, [])

  const signOut = useCallback(async () => {
    await logout()
    // React Router navigates inside a transition. Clearing the user in the same
    // transition makes both happen in one render; otherwise a page behind
    // <RequireAuth> would see "no user" first and bounce to the sign-in form.
    startTransition(() => {
      navigate('/', { replace: true })
      setUser(null)
    })
  }, [navigate])

  const value = useMemo<Auth>(
    () => ({ user, signIn, signUp, signOut, setUser }),
    [user, signIn, signUp, signOut],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
