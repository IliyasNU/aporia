# Aporia

A publishing platform for philosophical essays: authors publish, readers follow authors,
subscribe to email updates and get transparent, explainable recommendations.
Built with FastAPI, React and PostgreSQL.

> **Status: Stage 1 (Accounts), API only.** Registration, login/logout with server-side
> sessions, profiles and topic interests work through the API. Articles, subscriptions,
> recommendations and the web UI for accounts are **not implemented yet**. See
> [docs/roadmap.md](docs/roadmap.md).

## Quick start (Docker)

Requirements: Docker with the Compose plugin. No accounts, API keys or secrets are needed.

```bash
docker compose up --build
```

| URL                                 | What                                |
| ----------------------------------- | ----------------------------------- |
| http://localhost:8080               | Web app (React SPA served by nginx) |
| http://localhost:8000/api/v1/health | API liveness check (API + database) |
| http://localhost:8000/api/v1/docs   | OpenAPI / Swagger UI                |

Compose starts four services: `db` (PostgreSQL 16), `migrate` (runs `alembic upgrade head`
once and exits), `api` (FastAPI) and `web` (nginx serving the SPA and proxying `/api`).
All ports are bound to `127.0.0.1` only. To change ports or the database password, copy
`.env.example` to `.env` and edit it.

Stop with `docker compose down` (data is kept in the `db-data` volume) or
`docker compose down --volumes` (also deletes the database).

## Local development

Run the database in Docker and the code on your machine.

```bash
docker compose up -d db          # PostgreSQL on localhost:5432 (user/password: aporia)
```

### Backend (Python 3.12+, [uv](https://docs.astral.sh/uv/))

```bash
cd backend
uv sync                          # create .venv and install dependencies
uv run alembic upgrade head      # apply migrations
uv run uvicorn app.main:app --reload
```

The API is now on http://localhost:8000. Settings come from environment variables (or
`backend/.env`):

| Variable            | Default                                                                       |
| ------------------- | ----------------------------------------------------------------------------- |
| `DATABASE_URL`      | `postgresql+psycopg://aporia:aporia@localhost:5432/aporia`                    |
| `APP_ENV`           | `development` (`development`, `test` or `production`)                         |
| `LOG_LEVEL`         | `INFO`                                                                        |
| `TRUSTED_ORIGINS`   | local web, Vite and Swagger origins (comma-separated list, CSRF check)        |
| `SESSION_TTL_DAYS`  | `14`                                                                          |
| `TEST_DATABASE_URL` | `postgresql+psycopg://aporia:aporia@localhost:5432/aporia_test` (pytest only) |

New migration after changing a model:

```bash
uv run alembic revision --autogenerate --rev-id 0003 -m "short description"
```

### Frontend (Node.js 22+)

```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173, /api is proxied to :8000
```

## API

All endpoints live under `/api/v1`; the full contract with request and response schemas
is in the OpenAPI docs at `/api/v1/docs`. Errors always look like
`{"error": {"code": "...", "message": "..."}}`.

| Method and path         | Auth     | What it does                                         |
| ----------------------- | -------- | ---------------------------------------------------- |
| `GET /health`           | —        | Liveness: API and database                           |
| `POST /auth/register`   | —        | Create an account and sign in                        |
| `POST /auth/login`      | —        | Sign in with email and password                      |
| `POST /auth/logout`     | optional | End the current session                              |
| `GET /auth/me`          | required | Own account: email, profile, interests               |
| `PATCH /me/profile`     | required | Edit display name, bio, website                      |
| `PUT /me/interests`     | required | Replace topic interests, e.g. `{"tags": ["ethics"]}` |
| `GET /authors/{handle}` | —        | Public author profile                                |

Signing in sets an `HttpOnly`, `SameSite=Lax` session cookie (`Secure` when
`APP_ENV=production`). `POST`, `PATCH`, `PUT` and `DELETE` requests sent by a browser must
come from one of `TRUSTED_ORIGINS`, otherwise they get `403 csrf_failed`.

Try it with curl (no Origin header, so the CSRF check does not apply):

```bash
curl -c jar.txt -H 'Content-Type: application/json' \
  -d '{"email":"ada@example.com","password":"correct horse battery staple","handle":"ada","display_name":"Ada"}' \
  http://localhost:8000/api/v1/auth/register
curl -b jar.txt http://localhost:8000/api/v1/auth/me
```

## Checks

These are the same commands CI runs.

```bash
# backend/ (needs the db container running; tests create and wipe the "aporia_test" database)
uv run ruff check .
uv run ruff format --check .
uv run pytest

# frontend/
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
```

## Verification status

What is checked automatically on every push and pull request
([.github/workflows/ci.yml](.github/workflows/ci.yml)) and what has only been checked by hand.

| Check                                                                      | How       |
| -------------------------------------------------------------------------- | --------- |
| Backend lint and formatting (ruff)                                         | Automatic |
| Backend tests against PostgreSQL 16: health, error format, migrations      | Automatic |
| Auth: Argon2id hashes, sessions, logout, expired/tampered/replayed cookies | Automatic |
| Auth: same answer for unknown email and wrong password                     | Automatic |
| CSRF: untrusted Origin/Referer rejected, trusted and non-browser allowed   | Automatic |
| Profiles: input limits, own profile only, public view hides email          | Automatic |
| No passwords, session tokens or emails in application logs                 | Automatic |
| Migrations apply to an empty database, downgrade and re-apply              | Automatic |
| ORM models match migrations (`alembic check`)                              | Automatic |
| Frontend lint, formatting, typecheck, unit tests, production build         | Automatic |
| `docker compose up` from scratch: images build, API and web healthy        | Automatic |
| Page layout at 360 px and 1280 px, no horizontal scroll                    | Manual    |
| API returns 503 and the page shows it when the database is stopped         | Manual    |
| Data survives `docker compose down` / `up`                                 | Manual    |
| Full auth flow in Chromium through nginx; cookie unreadable from JS        | Manual    |
| Cross-site form POST from another origin is blocked in Chromium            | Manual    |

## Project structure

```
backend/        FastAPI app, Alembic migrations, pytest suite
  app/api/      HTTP routers (all under /api/v1)
  app/core/     settings, logging, error handling
  app/db/       SQLAlchemy base and session
  app/models/   ORM models
  app/schemas/  Pydantic request/response models
  app/services/ business logic (auth, users) called by the routers
frontend/       React + TypeScript + Vite + Tailwind SPA
docs/           architecture notes and roadmap
docker-compose.yml
```

More detail and the reasoning behind the main technical choices:
[docs/architecture.md](docs/architecture.md).

## License

[MIT](LICENSE)
