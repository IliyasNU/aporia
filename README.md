# Aporia

A publishing platform for philosophical essays: authors publish, readers follow authors,
subscribe to email updates and get transparent, explainable recommendations.
Built with FastAPI, React and PostgreSQL.

> **Status: Stage 0 (Foundation).** The repository, database, migrations, CI and a minimal
> web page are in place. Accounts, articles, subscriptions and recommendations are **not
> implemented yet**. See [docs/roadmap.md](docs/roadmap.md).

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
| `TEST_DATABASE_URL` | `postgresql+psycopg://aporia:aporia@localhost:5432/aporia_test` (pytest only) |

New migration after changing a model:

```bash
uv run alembic revision --autogenerate --rev-id 0002 -m "short description"
```

### Frontend (Node.js 22+)

```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173, /api is proxied to :8000
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

| Check                                                                 | How       |
| --------------------------------------------------------------------- | --------- |
| Backend lint and formatting (ruff)                                    | Automatic |
| Backend tests against PostgreSQL 16: health, error format, migrations | Automatic |
| Migrations apply to an empty database, downgrade and re-apply         | Automatic |
| ORM models match migrations (`alembic check`)                         | Automatic |
| Frontend lint, formatting, typecheck, unit tests, production build    | Automatic |
| `docker compose up` from scratch: images build, API and web healthy   | Automatic |
| Page layout at 360 px and 1280 px, no horizontal scroll               | Manual    |
| API returns 503 and the page shows it when the database is stopped    | Manual    |
| Data survives `docker compose down` / `up`                            | Manual    |

## Project structure

```
backend/        FastAPI app, Alembic migrations, pytest suite
  app/api/      HTTP routers (all under /api/v1)
  app/core/     settings, logging, error handling
  app/db/       SQLAlchemy base and session
  app/models/   ORM models
  app/schemas/  Pydantic request/response models
frontend/       React + TypeScript + Vite + Tailwind SPA
docs/           architecture notes and roadmap
docker-compose.yml
```

More detail and the reasoning behind the main technical choices:
[docs/architecture.md](docs/architecture.md).

## License

[MIT](LICENSE)
