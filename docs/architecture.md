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
