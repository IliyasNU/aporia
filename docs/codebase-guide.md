# A guided tour of the code

This guide is for a developer who knows some Python and JavaScript and wants to
understand, change or extend Aporia. Read it with the code open.

## 1. Follow one request

Take "publish an essay": the browser calls `POST /api/v1/articles/{id}/publish`.

1. **nginx** (`frontend/nginx.conf`) receives it on port 8080 and forwards `/api/` to
   the `api` container.
2. **Middlewares** in `backend/app/main.py` run first: the body-size check and the CSRF
   check (`app/core/csrf.py`), which rejects state-changing requests from other sites.
3. **The router** `backend/app/api/articles.py` matches `publish_article`. Its parameters
   tell FastAPI what it needs:
   - `article_id: uuid.UUID`: parsed from the path, 422 if it is not a UUID;
   - `user: CurrentUser`: the dependency in `app/api/deps.py` reads the session cookie,
     looks the session up and returns the `User`, or answers 401;
   - `db: DbSession`: a SQLAlchemy session for this request (`app/db/session.py`).
4. **The service** `app/services/articles.py` holds the rules: `get_own_article` gives 404
   or 403, `publish_article` refuses an empty body, sets `published_at` on the first
   publication and queues emails (`app/services/newsletter.py`) in the same transaction.
5. **Errors** are `AppError(status, code, message)`; `app/core/errors.py` turns them into
   `{"error": {"code": ..., "message": ...}}`.
6. **The response model** (`ArticleOut` in `app/schemas/articles.py`) decides exactly which
   fields leave the server. Nothing else is serialised by accident.

Routers stay thin (parse input, call a service, shape output); services hold the logic and
the SQL. There are no repository classes or other extra layers.

## 2. Where things live

```
backend/app/
  main.py            app factory: middlewares, error handlers, routers
  api/               one router per area: auth, me, authors, articles, social,
                     moderation, newsletter, feed, tags, health
  core/              config (settings from env), security (hashing, tokens),
                     csrf, rate_limit, errors, logging
  db/                Base with naming conventions and UUID/timestamp mixins; session
  models/            SQLAlchemy tables: user, tag, article, social, newsletter
  schemas/           Pydantic request/response models (validation and limits)
  services/          business logic: auth, users, articles, tags, social, comments,
                     moderation, newsletter, mailer, ranking (pure), recommendations,
                     maintenance, demo, visibility
  worker/            the email worker (`python -m app.worker`) and its healthcheck
  cli.py             admin commands (`python -m app.cli …`)
backend/alembic/     migrations 0001…0005
backend/tests/       pytest suite, one file per feature

frontend/src/
  main.tsx, App.tsx  router and routes
  api/               one typed function per endpoint, ApiError
  auth/              AuthProvider + useAuth (who is signed in)
  hooks/             useAsync (loading/success/error), useDocumentTitle
  pages/             one component per screen
  components/        layout, cards, forms, Markdown, buttons, states
  test/api.tsx       fake API and fixtures for tests
```

## 3. Rules the code relies on

- **One visibility rule.** `app/services/visibility.py` defines "the public may see this
  article" (published, not deleted, not hidden). Every public query uses it. If you add a
  new public list, use it too.
- **Owner checks in the query path.** Editing goes through `get_own_article` /
  `get_own_comment`; they return 404 for missing items and 403 for other people's.
- **The database guards invariants.** Unique pairs (follows, bookmarks, email jobs), check
  constraints on statuses, foreign keys with deliberate `ON DELETE CASCADE`. Code handles
  the resulting `IntegrityError` or uses `ON CONFLICT DO NOTHING` where repeating is fine.
- **Only hashes of secrets.** Passwords (Argon2id), session tokens and email tokens are
  stored hashed. Never log them, nor email addresses.
- **UTC everywhere.** Columns are `timestamptz`; Python uses `datetime.now(UTC)`.

## 4. Common tasks

**Add a field to a table**

1. Change the model in `app/models/…`.
2. `cd backend && uv run alembic revision --autogenerate --rev-id 0006 -m "describe it"`.
3. Read the generated file in `alembic/versions/`; autogenerate misses some things
   (for example `CHECK` constraints on existing tables).
4. `uv run alembic upgrade head`, then `uv run pytest` (a test fails if a model and the
   migrations disagree).

**Add an endpoint**

1. Request/response models in `app/schemas/`, with length limits.
2. Logic in a service function; raise `AppError` for expected failures.
3. A thin route in `app/api/…` with `responses=error_responses(...)` for the docs.
   Mutating routes must take `CurrentUser` unless they are public on purpose: a test in
   `tests/test_security.py` checks every POST/PUT/PATCH/DELETE and will remind you.
4. Tests in `backend/tests/`: use the `client`, `make_client`, `register`,
   `write_article`, `publish`, `signed_in` and `outbox` helpers from `tests/conftest.py`.

**Add a page**

1. A function in `src/api/…` for each endpoint it needs.
2. A component in `src/pages/` that loads data with `useAsync(key, load)` and renders
   loading, error (with retry) and empty states.
3. A `<Route>` in `src/App.tsx` (wrap it in `<RequireAuth>` if it needs an account).
4. A test with `mockApi({...})` and `renderApp('/path')` from `src/test/api.tsx`.

## 5. How tests work

- **Backend:** a real PostgreSQL database (`aporia_test`, created automatically and wiped
  at the start of each run). Every test runs inside a transaction that is rolled back, so
  tests do not see each other's data. Email sending is replaced by an in-memory `outbox`.
  Rate limits are off except in `test_security.py`.
- **Frontend:** Vitest + Testing Library in jsdom. `mockApi` replaces `fetch` with a small
  fake API; tests click and type like a user (`userEvent`) and assert on what is visible.
- **End to end:** `scripts/e2e_smoke.py` drives the running Docker stack through nginx and
  reads real emails from Mailpit. CI runs it on every push.

## 6. Things that look odd but are on purpose

- Email links carry tokens after `#`: browsers never send that part to servers, so tokens
  stay out of access logs. The confirm/unsubscribe pages act only on a button press.
- The unsubscribe token is an HMAC of the subscription id, so each email can carry a
  working link while the database stores only a hash.
- `useAsync` takes a string `key` instead of a dependency array; the key changes whenever
  the request should run again.
- Sign-out navigates and clears the user inside one React transition, so protected pages
  do not flash the sign-in form.
- `ScrollToTop` wraps `window.scrollTo` in braces: newer browsers return a Promise from it,
  and an effect must not return one.
