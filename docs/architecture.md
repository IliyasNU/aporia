# Architecture

Aporia is deliberately simple: one FastAPI service, one PostgreSQL database, one React
SPA and one email worker process. No microservices, message brokers,
Kubernetes or paid AI APIs.

```
browser ──► web (nginx) ──/api──► api (FastAPI) ──► db (PostgreSQL 16) ◄── worker ──► SMTP
               │                                      ▲                            (Mailpit
               └── static SPA files                   │                             locally)
                                    migrate (Alembic, runs once at startup)
```

## Stack

| Layer    | Choice                                                  |
| -------- | ------------------------------------------------------- |
| Backend  | Python 3.12, FastAPI, Pydantic v2, pydantic-settings    |
| Database | PostgreSQL 16, SQLAlchemy 2 (sync), Alembic, psycopg 3  |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4              |
| Tests    | pytest + Starlette TestClient; Vitest + Testing Library |
| Tooling  | uv, ruff; npm, ESLint, Prettier                         |
| Delivery | Docker Compose, GitHub Actions                          |

## Decisions

**UUID primary keys everywhere.** IDs appear in public URLs (`/articles/{id}`,
`/authors/{id}/follow`). Random UUIDs do not reveal how many users or articles exist and
cannot be enumerated. Python generates them (`uuid.uuid4`) so an object's id is known
before INSERT; the database default `gen_random_uuid()` covers raw SQL such as seed data.
See `UUIDPrimaryKeyMixin` in `backend/app/db/base.py`.

**Timestamps are `timestamptz` and stored in UTC.**

**Synchronous SQLAlchemy.** FastAPI runs sync endpoints in a thread pool, which is plenty
for this project and keeps the code easier to read and test than async sessions.

**Same origin for SPA and API.** In development Vite proxies `/api` to the API; in
Docker Compose nginx does. The browser only ever talks to one origin, so CORS is not
enabled at all and session cookies can be `SameSite=Lax` without cross-site setup.

**Migrations are the only way the schema changes.** Alembic migrations create every
table and seed data; `Base.metadata.create_all` is never used. In Compose a one-off
`migrate` service runs `alembic upgrade head` and the API starts only after it succeeds.
A test runs `alembic check` so a model change without a migration fails CI.
Each stage adds the tables it needs in its own migration.

**One error format.** Every error response is
`{"error": {"code": "not_found", "message": "Not Found"}}`. Validation errors add
`details` with field locations, but never echo submitted values (they may be passwords).
Unexpected exceptions return a generic 500 and are logged server-side.
See `backend/app/core/errors.py`.

**Tests use a real PostgreSQL database.** SQLite behaves differently (types, constraints,
`gen_random_uuid()`), so it is not used even in tests. Each test runs inside a
transaction that is rolled back afterwards.

**Secrets stay out of git and logs.** Configuration comes from environment variables;
`DATABASE_URL` is a `SecretStr` so it never shows up in a repr or log line. The values in
`docker-compose.yml` and `.env.example` are local-development defaults only.

## Authentication (Stage 1)

The goal is a small, conventional and testable setup: no JWT, OAuth or refresh tokens.

- **Passwords** are hashed with Argon2id (`argon2-cffi`, library defaults following
  RFC 9106). Hashes made with older parameters are upgraded on the next successful login.
- **Sessions** are rows in the `sessions` table. The cookie `aporia_session` holds a
  random 256-bit token; the database stores only its SHA-256 hash, so a database leak does
  not leak usable sessions. A session is valid until `expires_at` (`SESSION_TTL_DAYS`,
  default 14) or until logout sets `revoked_at`. Signing in or registering again in the
  same browser revokes that browser's previous session.
- **Cookie flags:** `HttpOnly` (JavaScript cannot read it), `SameSite=Lax` (not sent with
  cross-site POSTs), `Path=/`, and `Secure` when `APP_ENV=production`.
- **CSRF:** a middleware (`app/core/csrf.py`) rejects `POST`/`PUT`/`PATCH`/`DELETE` whose
  `Origin` (or, if missing, `Referer`) is not in `TRUSTED_ORIGINS`. Requests with neither
  header (curl, server-to-server) cannot carry a victim's browser cookie and are allowed.
- **No account enumeration on login:** unknown email and wrong password return the same
  `401 invalid_credentials`, and an unknown email still runs one Argon2 verification so the
  response time is similar. Registration does answer `409 email_taken`; avoiding that
  would need email verification, which is not part of v1.0. Login and registration are rate
  limited (see "Release hardening").
- **Roles:** `user` (every account can read and write) and `admin` (moderation, Stage 4).
  The API never lets users change their own role, email or handle.
- **Privacy:** the public author profile shows handle, display name, bio and website, never
  the email, role or interests.

## Articles (Stage 2)

- **Status** is `draft` → `published` ⇄ `unpublished`. Publishing is its own action
  (`POST /articles/{id}/publish`), never a field in an edit. An empty body cannot be
  published.
- **Slugs** come from the title (`slugify`, keeps non-Latin letters) and get a short random
  suffix when taken. While an article is a draft the slug follows the title; from the first
  publication on it never changes, so shared links keep working.
- **`published_at`** is the time of the first publication and is never reset. Stage 5 uses
  it to send new-article emails exactly on the first publication, not on edits or
  republishing.
- **Soft delete** sets `deleted_at`. The row stays (comments, bookmarks and email jobs can
  still reference it), but nobody, including the author, can open it again.
- **Visibility** is defined once in `app/services/visibility.py`: published, not deleted
  and not hidden by a moderator. Every public list, the search, tag
  counts and later the feeds and recommendations use it.
- **Markdown** is stored and returned as raw text. The API never renders HTML; the frontend
  renders Markdown with raw HTML disabled (SEC-02).
- **Lists** load authors with a join and tags with one extra `IN` query, so a page costs
  the same number of SQL queries whatever its size (a test checks this).

## Frontend (Stage 3)

- **Routing:** `react-router` in declarative mode (`<Routes>` in `src/App.tsx`). Pages that
  need an account are wrapped in `<RequireAuth>`, which sends guests to
  `/signin?next=…`. `safeNext()` only accepts same-site paths, so `?next=` cannot be used
  to redirect people to another site.
- **Data:** `src/api/*.ts` has one small function per endpoint on top of `api()`, which
  throws `ApiError` (status, code, message, field errors) for non-2xx answers. Pages load
  data with `useAsync(key, load)`: it tracks loading / success / error, cancels outdated
  requests and offers `reload()` for retry buttons. No global state library.
- **Who is signed in:** `AuthProvider` asks `/auth/me` once and shares the result with
  `useAuth()`. Signing out navigates and clears the user in one transition, so protected
  pages do not flash the sign-in form.
- **Markdown (SEC-02):** `components/Markdown.tsx` uses `react-markdown` with `skipHtml`
  (raw HTML is dropped, never executed), its default URL filter (no `javascript:` links),
  `rel="nofollow ugc"` on links, and images shown as links so authors cannot track readers
  with remote images.
- **Forms** never clear what the user typed when the server fails, and show field-level
  messages from 422 responses.
- **Styling:** Tailwind CSS with the typography plugin for long-form text; colours are
  theme tokens in `src/index.css`. No component library.
- **Accessibility:** skip link, semantic headings and landmarks, labelled inputs,
  `role="status"`/`role="alert"` for async messages, visible focus outlines.
- **SEO:** each page sets `<title>`, the meta description and Open Graph title/description.
  Server-side rendering and a sitemap are optional per the spec and not included.

## Social features and moderation (Stage 4)

- **Unique pairs in the database:** `follows (follower_id, author_id)` and
  `bookmarks (user_id, article_id)` use the pair as primary key, so duplicates are
  impossible. The API inserts with `ON CONFLICT DO NOTHING`, which makes following or
  saving twice (even at the same moment) harmless. A `CHECK` constraint forbids following
  yourself.
- **Comments** are plain text (never Markdown or HTML), flat, at most 2000 characters,
  soft-deleted, and only shown while their article is public.
- **Reports** point at an article or comment (`target_type` + `target_id`, no foreign key
  because the target table varies; the service checks the target exists and is public).
  One report per user and target.
- **Moderation:** `moderation_status` (`visible` / `hidden`) on articles and comments.
  Only users with `role = 'admin'` may call `/admin/*`. Hiding closes the target's open
  reports. Admins are assigned with `python -m app.cli set-role`, never through the API.
- **Popularity** (`sort=popular`) counts bookmarks with a correlated subquery; ties fall
  back to newest first.

## Email subscriptions (Stage 5)

- **Independent of accounts:** a subscription is (author, normalized email). Anyone can
  subscribe; an account is not needed and not linked.
- **Double opt-in:** nothing but the confirmation email is ever sent to a pending address.
  `request_subscription` answers identically in every case, and a pending address gets at
  most one confirmation email per `NEWSLETTER_RESEND_MINUTES`.
- **Tokens:** confirmation tokens are random (`secrets.token_urlsafe`), expire, and only
  their SHA-256 hash is stored. The unsubscribe token must work in every future email, so
  it is `HMAC(SECRET_KEY, subscription id)`: the worker recomputes it per email, the
  database stores only its hash, and nobody without the key can forge one. Rotating
  `SECRET_KEY` therefore invalidates old unsubscribe links.
- **Links** put tokens after `#` (never sent to servers, so never in logs), and the pages
  act only on a button press (a `POST`), so mail scanners that open links change nothing.
- **Outbox pattern:** publishing writes `email_jobs` rows in the same transaction; SMTP
  only happens in the worker. A broken mail server can never block or undo a publication.
- **Worker:** `SELECT … FOR UPDATE SKIP LOCKED` picks one due job at a time, so several
  worker processes would not send the same job twice. Retries back off 1 → 5 → 25 → 125
  minutes (capped at 6 hours) up to `WORKER_MAX_ATTEMPTS`; 5xx answers fail at once.
  Before sending it re-checks that the subscription is confirmed and the essay public.
- **Header injection:** subjects are built from user content (titles), so newlines are
  collapsed before they become headers.

## Recommendations (Stage 6)

- **Two layers.** `ranking.py` is pure: it takes plain dataclasses (`Candidate`, `Reader`)
  and a fixed `now`, and returns a ranked list. No database or clock inside, so tests can
  use hand-calculated examples. `recommendations.py` does the I/O: one query for
  candidates (with authors and tags), one for bookmark counts, one each for the reader's
  interests and follows: always 4 queries, however many essays.
- **Bounded work.** Only the newest 300 public essays are candidates. The greedy diversity
  step scans candidates by base score and stops once nobody below can catch up (diversity
  adds at most 0.05), which gives the same order as the plain O(n²) definition in about
  35 ms for 300 candidates.
- **Limiting hits.** Popularity uses `log1p`, so an essay with 10 bookmarks keeps about a
  third of the signal of one with 1000.
- **Explanations.** The reason is the component with the largest weighted contribution;
  ties prefer following, then interests, then popularity, then freshness.
- **Privacy.** Nothing is tracked to recommend: no views, clicks or reading time.

## Release hardening (Stage 7)

- **Rate limits** (`app/core/rate_limit.py`): sliding windows in memory, keyed by client IP,
  email or user id, with `429` and `Retry-After`. One API process makes this exact; with
  several processes each would count separately (documented).
- **Client IP:** nginx overwrites `X-Forwarded-For` with the address it sees, and uvicorn
  (`--proxy-headers`, `FORWARDED_ALLOW_IPS`) trusts it. That is safe because Docker
  Compose does not publish the API port: only nginx can reach the API.
- **Logs:** SQL parameters are never logged (`hide_parameters=True`), and database errors
  are logged without their message text, which PostgreSQL may fill with input values.
- **Input:** request bodies inherit `RequestModel`, which refuses NUL characters; a
  middleware does the same for paths and query strings.
- **Request size:** nginx `client_max_body_size 512k` and an API middleware returning 413.
- **Headers:** CSP, `X-Frame-Options`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`.
- **Operations:** maintenance commands in `app/cli.py`; the worker also removes ended
  sessions; Docker rotates logs; `scripts/e2e_smoke.py` checks the whole chain in CI.
