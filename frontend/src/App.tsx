import { useEffect } from 'react'
import { Route, Routes, useLocation } from 'react-router'

import { AuthProvider } from './auth/AuthProvider'
import { Layout } from './components/Layout'
import { RequireAuth } from './components/RequireAuth'
import { AccountPage } from './pages/AccountPage'
import { ArticlePage } from './pages/ArticlePage'
import { AuthorPage } from './pages/AuthorPage'
import { EditorPage } from './pages/EditorPage'
import { FollowingPage } from './pages/FollowingPage'
import { ForYouPage } from './pages/ForYouPage'
import { HomePage } from './pages/HomePage'
import { ConfirmSubscriptionPage, UnsubscribePage } from './pages/NewsletterPages'
import { NotFoundPage } from './pages/NotFoundPage'
import { SignInPage } from './pages/SignInPage'
import { SignUpPage } from './pages/SignUpPage'

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    // Braces matter: newer browsers return a Promise from scrollTo, and an
    // effect must return nothing or a cleanup function.
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}

export default function App() {
  return (
    <AuthProvider>
      <ScrollToTop />
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/for-you" element={<ForYouPage />} />
          <Route path="/articles/:slug" element={<ArticlePage />} />
          <Route path="/authors/:handle" element={<AuthorPage />} />
          <Route path="/signin" element={<SignInPage />} />
          <Route path="/signup" element={<SignUpPage />} />
          <Route path="/newsletter/confirm" element={<ConfirmSubscriptionPage />} />
          <Route path="/newsletter/unsubscribe" element={<UnsubscribePage />} />
          <Route
            path="/write"
            element={
              <RequireAuth>
                <EditorPage />
              </RequireAuth>
            }
          />
          <Route
            path="/write/:id"
            element={
              <RequireAuth>
                <EditorPage />
              </RequireAuth>
            }
          />
          <Route
            path="/following"
            element={
              <RequireAuth>
                <FollowingPage />
              </RequireAuth>
            }
          />
          <Route
            path="/account"
            element={
              <RequireAuth>
                <AccountPage />
              </RequireAuth>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Layout>
    </AuthProvider>
  )
}
