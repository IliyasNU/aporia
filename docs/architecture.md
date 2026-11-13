# Architecture

Aporia is deliberately simple: one FastAPI service, one PostgreSQL database, one React
SPA and, from Stage 5, one email worker process. No microservices, message brokers,
Kubernetes or paid AI APIs.

```
browser ──► web (nginx) ──/api──► api (FastAPI) ──► db (PostgreSQL 16)
               │                                      ▲
               └── static SPA files                   │
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
  would need email verification, which is not part of v1.0. Rate limiting of login and
  registration (SEC-03) is planned for Stage 7.
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
- **Visibility** is defined once in `app/services/visibility.py`: published and not
  deleted (Stage 4 adds "not hidden by a moderator"). Every public list, the search, tag
  counts and later the feeds and recommendations use it.
- **Markdown** is stored and returned as raw text. The API never renders HTML; the frontend
  renders Markdown with raw HTML disabled (SEC-02).
- **Lists** load authors with a join and tags with one extra `IN` query, so a page costs
  the same number of SQL queries whatever its size (a test checks this).
