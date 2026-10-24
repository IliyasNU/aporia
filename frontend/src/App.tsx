import { ApiStatus } from './components/ApiStatus'

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-rule">
        <div className="mx-auto max-w-3xl px-4 py-5">
          <span className="font-serif text-2xl font-semibold tracking-tight">Aporia</span>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12">
        <h1 className="font-serif text-3xl leading-tight font-semibold sm:text-4xl">
          A home for philosophical essays
        </h1>
        <p className="mt-4 max-w-prose text-lg leading-relaxed text-muted">
          Aporia is under construction. Reading, publishing, author subscriptions and transparent
          recommendations will arrive in the upcoming releases.
        </p>

        <section aria-labelledby="status-heading" className="mt-10 border-t border-rule pt-6">
          <h2 id="status-heading" className="text-sm font-semibold tracking-wide uppercase">
            System status
          </h2>
          <div className="mt-3">
            <ApiStatus />
          </div>
        </section>
      </main>

      <footer className="border-t border-rule">
        <div className="mx-auto max-w-3xl px-4 py-5 text-sm text-muted">
          Aporia · v0.1 development build
        </div>
      </footer>
    </div>
  )
}
