# Aporia

A publishing platform for philosophical essays. Authors write and publish in Markdown;
readers follow authors, save essays, comment, subscribe to new essays by email and get
transparent recommendations that say why they were picked. Built with FastAPI, React and
PostgreSQL. No paid services, no AI APIs, no trackers.

> **Status: v1.0 release candidate.** Every requirement of the v1.0 specification is
> implemented and tested (see [docs/roadmap.md](docs/roadmap.md) and the
> [release checklist](docs/release-checklist.md)). The code lives in stacked pull requests
> (Stage 0 to Stage 7) awaiting the owner's review; nothing is deployed publicly.

## What you can do

- **Read** essays without an account: search, filter by topic, sort by newest or most
  saved, open author pages.
- **Write**: sign up, draft in Markdown with a preview, publish, edit (links stay stable),
  unpublish or delete.
- **Follow and save**: follow authors (with a _Following_ feed), save essays, comment.
- **Subscribe by email** to an author without an account: double opt-in, one email per
  new essay, an unsubscribe link in every email.
- **For you**: recommendations from your interests, the authors you follow, what readers
  save and what is new, each with its reason. Guests get fresh and popular essays.
- **Moderation**: report essays and comments; administrators hide content and can remove
  it permanently.

## Quick start (Docker)

Requirements: Docker with the Compose plugin. No accounts, API keys or secrets are needed.

```bash
docker compose up --build
```

| URL                               | What                                        |
| --------------------------------- | ------------------------------------------- |
| http://localhost:8080             | The web app                                 |
| http://localhost:8080/api/v1/docs | API documentation (Swagger UI)              |
| http://localhost:8025             | Mailpit: every email the app sends, locally |

Compose starts `db` (PostgreSQL 16), `migrate` (applies migrations once, then exits),
`api` (FastAPI), `worker` (sends queued emails), `web` (nginx serving the app and proxying
`/api`) and `mailpit` (development SMTP inbox). All ports are bound to `127.0.0.1`.

Want content to click through? `docker compose exec api python -m app.cli seed-demo`
creates clearly labelled demo accounts and essays (sign in as
`demo_reader@example.com` / `demo-password`). A guided 5–7 minute demo is in
[docs/demo.md](docs/demo.md).

Stop with `docker compose down` (data is kept) or `docker compose down --volumes`
(deletes the database).

## Local development

Run PostgreSQL (and Mailpit) in Docker and the code on your machine:

```bash
docker compose up -d db mailpit
```

**Backend** (Python 3.12+, [uv](https://docs.astral.sh/uv/)):

```bash
cd backend
uv sync                              # install dependencies into .venv
uv run alembic upgrade head          # create the tables
uv run uvicorn app.main:app --reload # API on http://localhost:8000
uv run python -m app.worker          # second terminal: sends queued emails
```

**Frontend** (Node.js 22+):

```bash
cd frontend
npm install
npm run dev                          # http://localhost:5173, /api is proxied to :8000
```

New to the code? Start with the [codebase guide](docs/codebase-guide.md).

## Configuration

Settings come from environment variables (or `backend/.env`; for Docker, a root `.env`;
see `.env.example`). Every value has a working local default.

| Variable                 | Default / meaning                                                                                  |
| ------------------------ | -------------------------------------------------------------------------------------------------- |
| `APP_ENV`                | `development`; `production` enables `Secure` cookies and stricter checks                           |
| `DATABASE_URL`           | `postgresql+psycopg://aporia:aporia@localhost:5432/aporia`                                         |
| `SECRET_KEY`             | dev placeholder; **32+ random characters required in production**                                  |
| `PUBLIC_BASE_URL`        | `http://localhost:8080`, used in email links                                                       |
| `TRUSTED_ORIGINS`        | local origins; comma-separated browser origins allowed to change data                              |
| `SMTP_HOST`, `SMTP_PORT` | `localhost`, `1025` (Mailpit); plus `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_STARTTLS`, `MAIL_FROM` |
| `SESSION_TTL_DAYS`       | `14`                                                                                               |
| `RATE_LIMITS_ENABLED`    | `true`                                                                                             |
| `LOG_LEVEL`              | `INFO`                                                                                             |
| `TEST_DATABASE_URL`      | `…/aporia_test`, used by pytest and wiped on every run                                             |

Running it on a real server (HTTPS, SMTP, backups): [docs/deployment.md](docs/deployment.md).

## API

All endpoints are under `/api/v1` and documented in OpenAPI (`/api/v1/docs`). Errors
always look like `{"error": {"code": "...", "message": "..."}}`.

| Endpoints                                                                                                                         | Who              |
| --------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| `GET /health`                                                                                                                     | anyone           |
| `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`                                                    | session          |
| `PATCH /me/profile`, `PUT /me/interests`, `GET /authors/{handle}`                                                                 | owner / anyone   |
| `GET /articles` (`q`, `tag`, `author`, `sort=latest\|popular`, paging), `GET /articles/{slug}`, `GET /tags`                       | anyone           |
| `POST /articles`, `PATCH /articles/{id}`, `POST /articles/{id}/publish`, `POST /articles/{id}/unpublish`, `DELETE /articles/{id}` | author           |
| `GET /me/articles`, `GET /me/articles/{id}`                                                                                       | author           |
| `POST`/`DELETE /authors/{id}/follow`, `GET /me/following`, `GET /feed/following`                                                  | signed in        |
| `POST`/`DELETE /articles/{id}/bookmark`, `GET /me/bookmarks`                                                                      | signed in        |
| `GET`/`POST /articles/{id}/comments`, `PATCH`/`DELETE /comments/{id}`                                                             | anyone / owner   |
| `POST /reports`; `GET /admin/reports`, `POST /admin/moderate`                                                                     | signed in; admin |
| `POST /authors/{id}/newsletter-subscriptions`, `POST /newsletter/confirm`, `POST /newsletter/unsubscribe`                         | anyone (token)   |
| `GET /feed/recommended`                                                                                                           | anyone           |

Signing in sets an `HttpOnly`, `SameSite=Lax` session cookie. State-changing requests from
a browser must come from one of `TRUSTED_ORIGINS` (`403 csrf_failed` otherwise). Login,
registration, subscriptions, comments and reports are rate limited (`429` with
`Retry-After`).

## How the key parts work

- **Email subscriptions.** Double opt-in; the subscribe endpoint answers the same for
  every address. The first publication of an essay creates one job per confirmed
  subscriber in the same transaction; the `worker` sends them with retries (1, 5, 25,
  125 minutes; up to 5 attempts) and cancels jobs for people who unsubscribed. **Delivery
  is at least once:** a job is marked sent only after the SMTP server accepted it, so a
  worker crash between those two moments can send one duplicate. Exactly-once delivery is
  impossible with SMTP; Aporia never creates more than one job per essay and subscriber.
- **Recommendations.** One transparent formula in `backend/app/services/ranking.py`:
  `0.40 interests + 0.25 following + 0.15 log-popularity + 0.15 freshness + 0.05 diversity`,
  ordered by score, then date, then id. Every item states its main reason. Nothing is
  tracked to compute it.
- **Security.** Argon2id passwords, hashed session and email tokens, CSRF check, rate
  limits, safe Markdown rendering (raw HTML dropped), Content-Security-Policy, no secrets
  in logs. Details: [docs/security.md](docs/security.md).

## Administration

There is no admin panel (by design). Administrators use the API through Swagger UI while
signed in, and a few commands with server access:

```bash
docker compose exec api python -m app.cli set-role ada@example.com admin   # or: user
docker compose exec api python -m app.cli delete-article <article-id>      # permanent
docker compose exec api python -m app.cli delete-comment <comment-id>
docker compose exec api python -m app.cli delete-user ada@example.com      # with all content
docker compose exec api python -m app.cli delete-subscriber fan@example.com
```

`GET /admin/reports` lists open reports; `POST /admin/moderate` with
`{"target_type": "article" | "comment", "target_id": "…", "action": "hide" | "unhide"}`
hides content from every public view and closes its reports.

## Checks

The same commands CI runs ([.github/workflows/ci.yml](.github/workflows/ci.yml)):

```bash
cd backend  && uv run ruff check . && uv run ruff format --check . && uv run pytest
cd frontend && npm run lint && npm run format:check && npm run typecheck && npm test && npm run build
docker compose up --build --detach --wait && python3 scripts/e2e_smoke.py
```

Backend tests need the `db` container (they create and wipe `aporia_test`).

## Verification status

**Checked automatically on every push** (GitHub Actions):

- Backend: lint, formatting, about 250 tests against PostgreSQL 16 (auth, sessions,
  CSRF, profiles, articles, catalog, follows, bookmarks, comments, moderation, email
  subscriptions, worker, ranking, recommendations, rate limits, admin commands), migrations
  from an empty database and back, models matching migrations, no N+1 on lists, no
  secrets in logs, every mutating endpoint requiring a session unless public by design.
- Frontend: lint, formatting, type checking, about 60 component and page tests (states,
  forms keeping input, safe Markdown, redirects, social controls, email pages,
  recommendations), production build.
- Docker Compose from scratch: all images build, every service healthy, then
  `scripts/e2e_smoke.py`: register → publish → subscribe → confirm with the link from
  Mailpit → the worker emails the next essay → unsubscribe → recommendation with a reason.

**Checked by hand** (not repeated automatically):

- Chromium at 360 px and 1280 px for every screen: layout, no horizontal scroll, skip link
  and focus outlines, no Content-Security-Policy violations.
- Multi-user browser sessions: following, saving, commenting, reporting, hiding by an
  admin made with the CLI; a cross-site form POST being blocked.
- Mailpit stopped while publishing: the essay is published, the email is retried and
  delivered after Mailpit returns; the API returns 503 while the database is down.
- Data survives `docker compose down` / `up`.

The scenario-by-scenario list is in [docs/release-checklist.md](docs/release-checklist.md).

## Documentation

| Document                                               | For                                              |
| ------------------------------------------------------ | ------------------------------------------------ |
| [docs/codebase-guide.md](docs/codebase-guide.md)       | Understanding and extending the code             |
| [docs/architecture.md](docs/architecture.md)           | Technical decisions and why                      |
| [docs/security.md](docs/security.md)                   | Security and privacy, requirement by requirement |
| [docs/deployment.md](docs/deployment.md)               | Running it on a server                           |
| [docs/demo.md](docs/demo.md)                           | A 5–7 minute demo                                |
| [docs/release-checklist.md](docs/release-checklist.md) | Evidence for every end-to-end scenario           |
| [docs/roadmap.md](docs/roadmap.md)                     | Stages and requirement IDs                       |
| [CHANGELOG.md](CHANGELOG.md)                           | What v1.0 contains and its known limitations     |

## Project structure

```
backend/      FastAPI app (app/), Alembic migrations, pytest suite
frontend/     React + TypeScript + Vite + Tailwind single-page app, nginx config
scripts/      e2e_smoke.py: end-to-end check against the running stack
docs/         guides and decisions
docker-compose.yml
```

## License

[MIT](LICENSE)
