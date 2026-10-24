# Aporia

A publishing platform for philosophical essays: authors publish, readers follow authors,
subscribe to email updates and get transparent, explainable recommendations.
Built with FastAPI, React and PostgreSQL.

> **Status: Stage 6 (Recommendations).** Every v1.0 feature is implemented: accounts,
> publishing, search, follows, bookmarks, comments, moderation, double opt-in email
> subscriptions and explainable recommendations. Stage 7 (release hardening) is next. See
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
| http://localhost:8025               | Mailpit: every email the app sends  |

Compose starts six services: `db` (PostgreSQL 16), `migrate` (runs `alembic upgrade head`
once and exits), `api` (FastAPI), `worker` (sends queued emails), `web` (nginx serving the
SPA and proxying `/api`) and `mailpit` (a local SMTP server with a web inbox; development only).
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
uv run python -m app.worker      # in a second terminal: sends queued emails
```

The API is now on http://localhost:8000. Settings come from environment variables (or
`backend/.env`):

| Variable                 | Default                                                                                            |
| ------------------------ | -------------------------------------------------------------------------------------------------- |
| `DATABASE_URL`           | `postgresql+psycopg://aporia:aporia@localhost:5432/aporia`                                         |
| `APP_ENV`                | `development` (`development`, `test` or `production`)                                              |
| `LOG_LEVEL`              | `INFO`                                                                                             |
| `TRUSTED_ORIGINS`        | local web, Vite and Swagger origins (comma-separated list, CSRF check)                             |
| `SESSION_TTL_DAYS`       | `14`                                                                                               |
| `SECRET_KEY`             | dev placeholder (must be 32+ random characters in production)                                      |
| `PUBLIC_BASE_URL`        | `http://localhost:8080` (used in email links)                                                      |
| `SMTP_HOST`, `SMTP_PORT` | `localhost`, `1025` (Mailpit); also `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_STARTTLS`, `MAIL_FROM` |
| `TEST_DATABASE_URL`      | `postgresql+psycopg://aporia:aporia@localhost:5432/aporia_test` (pytest only)                      |

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

| Method and path                                            | Auth         | What it does                                                  |
| ---------------------------------------------------------- | ------------ | ------------------------------------------------------------- |
| `GET /health`                                              | —            | Liveness: API and database                                    |
| `POST /auth/register`                                      | —            | Create an account and sign in                                 |
| `POST /auth/login`                                         | —            | Sign in with email and password                               |
| `POST /auth/logout`                                        | optional     | End the current session                                       |
| `GET /auth/me`                                             | required     | Own account: email, profile, interests                        |
| `PATCH /me/profile`                                        | required     | Edit display name, bio, website                               |
| `PUT /me/interests`                                        | required     | Replace topic interests, e.g. `{"tags": ["ethics"]}`          |
| `GET /authors/{handle}`                                    | —            | Public author profile                                         |
| `GET /articles`                                            | —            | Published articles: `q`, `tag`, `author`, `page`, `page_size` |
| `GET /articles/{slug}`                                     | —            | One article (drafts only for their author)                    |
| `POST /articles`                                           | required     | Create a draft                                                |
| `PATCH /articles/{id}`                                     | owner        | Edit title, summary, Markdown body, tags                      |
| `POST /articles/{id}/publish`                              | owner        | Publish (slug is frozen from now on)                          |
| `POST /articles/{id}/unpublish`                            | owner        | Take a published article down                                 |
| `DELETE /articles/{id}`                                    | owner        | Soft delete                                                   |
| `GET /me/articles`                                         | required     | Own articles in every status                                  |
| `GET /me/articles/{id}`                                    | owner        | One own article in any status (for the editor)                |
| `GET /tags`                                                | —            | Tag catalog with published-article counts                     |
| `POST`/`DELETE /authors/{id}/follow`                       | required     | Follow / unfollow an author (idempotent)                      |
| `GET /me/following`, `GET /feed/following`                 | required     | Followed authors; their new essays                            |
| `POST`/`DELETE /articles/{id}/bookmark`                    | required     | Save / unsave a published essay                               |
| `GET /me/bookmarks`                                        | required     | Saved essays that are still public                            |
| `GET`/`POST /articles/{id}/comments`                       | — / required | Read / write plain-text comments                              |
| `PATCH`/`DELETE /comments/{id}`                            | owner        | Edit / delete your comment                                    |
| `POST /reports`                                            | required     | Report an article or comment                                  |
| `GET /admin/reports`, `POST /admin/moderate`               | admin        | Review reports; hide or unhide content                        |
| `POST /authors/{id}/newsletter-subscriptions`              | —            | Subscribe by email (double opt-in), always `202`              |
| `POST /newsletter/confirm`, `POST /newsletter/unsubscribe` | token        | Confirm / stop a subscription                                 |
| `GET /feed/recommended`                                    | optional     | Ranked essays with a `reason` each; cold start for guests     |

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

## Email subscriptions

Anyone can subscribe to an author's new essays from the author's page, without an account.

1. `POST /authors/{id}/newsletter-subscriptions` stores a **pending** subscription and emails
   a confirmation link (double opt-in). The answer is always the same `202`, so the endpoint
   cannot be used to find out who is subscribed. A new link is sent at most every 10 minutes.
2. The link opens `/newsletter/confirm#token=…`; pressing the button confirms
   (`POST /newsletter/confirm`). Tokens are random, single-purpose, expire after 48 hours and
   are stored only as SHA-256 hashes. They sit after `#`, which browsers never send to a
   server, so they cannot appear in access logs.
3. The **first** publication of an essay creates one row in `email_jobs` per confirmed
   subscriber, in the same transaction. Edits, unpublish/republish and repeated publish
   calls create nothing (`UNIQUE(article_id, subscription_id)`).
4. The `worker` service sends due jobs over SMTP, one at a time with a short pause (rate
   limit). Temporary errors (server down, 4xx) are retried after 1, 5, 25, 125 minutes;
   after 5 attempts, or on a permanent 5xx rejection, the job is marked `failed` with an
   `error_code`. Jobs for people who unsubscribed, or for essays no longer public, are
   `cancelled` instead of sent.
5. Every email has an unsubscribe link (and a `List-Unsubscribe` header) that works without
   signing in (`POST /newsletter/unsubscribe`).

**Delivery guarantee (and its limit).** A job is marked `sent` only after the SMTP server
accepted the message. If the worker crashes in between, the job is still `pending` and the
email is sent once more after restart. Exactly-once delivery cannot be guaranteed with
SMTP; Aporia guarantees _at least once_, with a duplicate possible only in that crash
window, and _never more than one job per essay and subscriber_.

**Production SMTP.** Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`,
`SMTP_STARTTLS=true`, `MAIL_FROM`, `PUBLIC_BASE_URL` (your site's URL, used in links) and a
random `SECRET_KEY` (32+ characters; it signs unsubscribe links, so keep it stable). Do not
run `mailpit` in production. No paid email service is required or configured.

Finished jobs are deleted after `EMAIL_JOB_RETENTION_DAYS` (90) and never-confirmed
subscriptions a week after their link expired.

## Recommendations

`GET /api/v1/feed/recommended` (the "For you" page) ranks the newest 300 public essays
with one transparent formula, implemented as a pure function in
`backend/app/services/ranking.py`:

```
score = 0.40 * tag_match    # share of the essay's tags among your interests (0..1)
      + 0.25 * following    # 1 if you follow the author
      + 0.15 * popularity   # log1p(bookmarks), relative to the most bookmarked candidate
      + 0.15 * freshness    # exp(-age_days / 30)
      + 0.05 * diversity    # share of the essay's tags not already shown above it
order: score DESC, published_at DESC, id DESC
```

- Each item carries a `reason` (its largest weighted signal): "You are interested in
  Ethics", "You follow David Hume", "Popular with readers" or "Recently published".
- Guests and readers without interests or follows get the same formula with only
  popularity, freshness and diversity (cold start, `cold_start: true`), so the feed is
  never empty and new essays without bookmarks still appear.
- Your own essays, essays you saved, and anything not public are left out.
- No embeddings, no LLMs, no click tracking: only interests, follows, bookmarks and dates.

## Moderation

There is no admin panel in v1.0 (by design). Make an account an administrator with a
command, then use the admin endpoints through Swagger UI (`/api/v1/docs`) while signed in:

```bash
docker compose exec api python -m app.cli set-role ada@example.com admin   # or: user
```

- `GET /api/v1/admin/reports` lists open reports (`?status=resolved` for closed ones).
- `POST /api/v1/admin/moderate` with
  `{"target_type": "article" | "comment", "target_id": "…", "action": "hide" | "unhide"}`
  hides or restores the content and closes its open reports.

Hidden articles disappear from every public list, search, feed, bookmark list and tag
count; their author still sees them with a "hidden by a moderator" notice.

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

| Check                                                                                         | How       |
| --------------------------------------------------------------------------------------------- | --------- |
| Backend lint and formatting (ruff)                                                            | Automatic |
| Backend tests against PostgreSQL 16: health, error format, migrations                         | Automatic |
| Auth: Argon2id hashes, sessions, logout, expired/tampered/replayed cookies                    | Automatic |
| Auth: same answer for unknown email and wrong password                                        | Automatic |
| CSRF: untrusted Origin/Referer rejected, trusted and non-browser allowed                      | Automatic |
| Profiles: input limits, own profile only, public view hides email                             | Automatic |
| Articles: drafts private, publish/unpublish/delete, only owner can change                     | Automatic |
| Articles: slug stays the same after first publish, empty body cannot publish                  | Automatic |
| Catalog: search (case, Unicode, wildcards), filters, pagination, 422s                         | Automatic |
| Catalog: drafts/unpublished/deleted never listed; no N+1 queries                              | Automatic |
| Frontend: pages render API data, loading/empty/error states, retry                            | Automatic |
| Frontend: Markdown drops HTML, strips javascript: links, no remote images                     | Automatic |
| Frontend: forms keep input on server errors; delete needs confirmation                        | Automatic |
| Frontend: sign-in redirects only to same-site paths                                           | Automatic |
| Social: follow/bookmark idempotent and unique, no self-follow, feed order                     | Automatic |
| Comments: length limits, own edit/delete only, hidden with their article                      | Automatic |
| Moderation: users get 403 on admin endpoints; hidden content gone everywhere                  | Automatic |
| UI: save/follow toggles, comments edit/delete/report, sort, following feed                    | Automatic |
| Email: double opt-in, same answer for every address, resend cooldown, tokens hashed           | Automatic |
| Email: expired/invalid tokens rejected, confirm and unsubscribe idempotent                    | Automatic |
| Email: one job per essay and subscriber; edits and republishing send nothing                  | Automatic |
| Worker: send, retry with backoff, give up, permanent failure, cancel, cleanup                 | Automatic |
| Worker: publishing works with SMTP down; logs hold no addresses or tokens                     | Automatic |
| Docker Compose: worker and Mailpit running                                                    | Automatic |
| Ranking: hand-calculated scenario, weights, log popularity, decay, diversity, ties            | Automatic |
| Feed: cold start for guests, reasons, excludes own/saved/non-public, 4 queries                | Automatic |
| No passwords, session tokens or emails in application logs                                    | Automatic |
| Migrations apply to an empty database, downgrade and re-apply                                 | Automatic |
| ORM models match migrations (`alembic check`)                                                 | Automatic |
| Frontend lint, formatting, typecheck, unit tests, production build                            | Automatic |
| `docker compose up` from scratch: images build, API and web healthy                           | Automatic |
| Page layout at 360 px and 1280 px, no horizontal scroll                                       | Manual    |
| API returns 503 and the page shows it when the database is stopped                            | Manual    |
| Data survives `docker compose down` / `up`                                                    | Manual    |
| Full auth flow in Chromium through nginx; cookie unreadable from JS                           | Manual    |
| Cross-site form POST from another origin is blocked in Chromium                               | Manual    |
| Full UI flow in Chromium at 360 px: sign up → write → publish → unpublish → delete            | Manual    |
| Keyboard: skip link first, visible focus; no horizontal scroll at 360 px                      | Manual    |
| Two readers and an admin in Chromium: save, follow, comment, report, hide via CLI-made admin  | Manual    |
| Real emails via Mailpit: subscribe → confirm → new essay → unsubscribe; SMTP outage and retry | Manual    |
| "For you" in Chromium: guest cold start and personalised reasons at 360 px                    | Manual    |

## Project structure

```
backend/        FastAPI app, Alembic migrations, pytest suite
  app/api/      HTTP routers (all under /api/v1)
  app/core/     settings, logging, error handling
  app/db/       SQLAlchemy base and session
  app/models/   ORM models
  app/schemas/  Pydantic request/response models
  app/services/ business logic (auth, users, articles, tags) called by the routers
frontend/       React + TypeScript + Vite + Tailwind SPA
  src/api/      typed fetch functions, one per endpoint
  src/auth/     who is signed in (AuthProvider, useAuth)
  src/pages/    one component per screen (FE-01..FE-05)
  src/components/ shared UI: layout, cards, forms, Markdown, states
docs/           architecture notes and roadmap
docker-compose.yml
```

More detail and the reasoning behind the main technical choices:
[docs/architecture.md](docs/architecture.md).

## License

[MIT](LICENSE)
