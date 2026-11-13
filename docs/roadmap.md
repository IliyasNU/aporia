# Roadmap (v1.0 MVP)

Each stage is a separate pull request into `main`. Nothing is merged without the
owner's approval. Requirement IDs refer to the v1.0 product requirements.

| Stage | Scope                                                         | Requirements              | Status        |
| ----- | ------------------------------------------------------------- | ------------------------- | ------------- |
| 0     | Foundation: repo layout, settings, Compose, migrations, CI    | —                         | **In review** |
| 1     | Accounts: register/login/logout, sessions, profile, interests | AUTH-01, AUTH-02, USER-01 | **In review** |
| 2     | Publishing: articles, drafts, tags, search, public API        | ART-01, ART-02, ART-03    | **In review** |
| 3     | Frontend: public pages, profiles, editor, personal area       | FE-01 … FE-05             | **In review** |
| 4     | Social: follows, bookmarks, comments, moderation              | SOC-01, SOC-02, MOD-01    | **In review** |
| 5     | Email: double opt-in, unsubscribe, DB-backed jobs, worker     | MAIL-01 … MAIL-04, FE-07  | **In review** |
| 6     | Recommendations: heuristic ranker, cold start, reasons        | REC-01 … REC-03, FE-06    | **In review** |
| 7     | Release: security hardening, Docker smoke, docs, demo         | SEC-01 … SEC-07           | Not started   |

## Stage 0: what exists

- `backend/`: FastAPI app with `GET /api/v1/health`, settings from environment
  variables, uniform JSON errors, SQLAlchemy 2 + Alembic. Migration `0001` creates the
  `tags` table and seeds the topic catalog (ethics, stoicism, existentialism,
  epistemology, metaphysics, consciousness, logic).
- `frontend/`: React + TypeScript + Vite + Tailwind app showing a placeholder page and
  the live API status.
- `docker-compose.yml`: `db`, `migrate`, `api`, `web`.
- CI: backend lint/format/tests, frontend lint/format/typecheck/tests/build, and a
  Docker Compose smoke test.

## Stage 1: what exists

- Migration `0002`: `users`, `sessions`, `user_interest_tags`.
- `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`,
  `PATCH /me/profile`, `PUT /me/interests`, `GET /authors/{handle}`.
- Argon2id password hashing, hashed server-side session tokens, `HttpOnly`/`SameSite=Lax`
  cookies (`Secure` in production), Origin/Referer CSRF check on state-changing requests.
- Not yet: rate limiting (Stage 7), the web UI for these features (Stage 3), admin
  assignment (Stage 4).

## Stage 2: what exists

- Migration `0003`: `articles` (status `draft` / `published` / `unpublished`,
  `published_at` = first publication, `deleted_at` for soft delete) and `article_tags`.
- `GET /articles` (search in title and summary, filter by `tag` and `author`, pagination),
  `GET /articles/{slug}`, `POST /articles`, `PATCH /articles/{id}`,
  `POST /articles/{id}/publish`, `POST /articles/{id}/unpublish`, `DELETE /articles/{id}`.
- Additions needed by the frontend: `GET /me/articles`, `GET /me/articles/{id}` (editor)
  and `GET /tags` (catalog with counts, for popular tags and pickers).
- One visibility rule (`app/services/visibility.py`) used by every public query.
- `sort=popular` (most bookmarked first) was added in Stage 4.

## Stage 3: what exists

Screens (React Router, all wired to the real API):

| Route                  | Screen                                                                                                  | Requirement |
| ---------------------- | ------------------------------------------------------------------------------------------------------- | ----------- |
| `/`                    | Essay list with search, popular tags, pagination, write CTA                                             | FE-01       |
| `/articles/:slug`      | Essay with safe Markdown, author, date, tags; edit link for the author                                  | FE-02       |
| `/authors/:handle`     | Public profile with bio, website and published essays                                                   | FE-03       |
| `/write`, `/write/:id` | Editor: title, summary, tags, Markdown with preview, save, publish, unpublish, delete with confirmation | FE-04       |
| `/account`             | Own essays in every status, profile, interests, sign out                                                | FE-05       |
| `/signin`, `/signup`   | Forms with field errors and safe `?next=` redirects                                                     | AUTH-01     |

- Loading, empty and error states (with retry) on every data view; checked at 360 px.
- Follow, bookmark and comment controls arrive with Stage 4; the newsletter form with Stage 5.

## Stage 4: what exists

- Migration `0004`: `follows`, `bookmarks` (composite primary keys = unique pairs),
  `comments`, `reports`, and `articles.moderation_status`.
- Follows: `POST/DELETE /authors/{id}/follow` (idempotent, not yourself),
  `GET /me/following`, `GET /feed/following`; `followed_by_me` on author profiles.
- Bookmarks: `POST/DELETE /articles/{id}/bookmark` (idempotent, public articles only),
  `GET /me/bookmarks`; `bookmarked_by_me` and `following_author` on article details;
  `GET /articles?sort=popular`.
- Comments: `GET/POST /articles/{id}/comments`, `PATCH/DELETE /comments/{id}` (own only,
  plain text up to 2000 characters, soft delete).
- Moderation: `POST /reports` (one per user and target), `GET /admin/reports`,
  `POST /admin/moderate` (admins only), `python -m app.cli set-role` to assign admins.
- UI: Save / Follow buttons, comments with edit, delete and report, report an essay,
  "Most saved" sort, `/following` feed, saved essays and followed authors in the account.

## Stage 5: what exists

- Migration `0005`: `email_subscriptions` (unique per author and normalized email, hashed
  tokens) and `email_jobs` (unique per article and subscription, status, attempts,
  next_retry_at, sent_at, error_code).
- `POST /authors/{id}/newsletter-subscriptions`, `POST /newsletter/confirm`,
  `POST /newsletter/unsubscribe`.
- Jobs are created in the transaction of the first publication; `python -m app.worker`
  sends them with retries, cancellation and cleanup. `worker` and `mailpit` services in
  Docker Compose.
- UI: subscribe form on author pages, `/newsletter/confirm` and `/newsletter/unsubscribe`
  pages that act only on a button press.

## Stage 6: what exists

- `app/services/ranking.py`: pure scoring with the spec's weights, log-scaled popularity,
  30-day freshness decay, a greedy diversity bonus, a stable tie-breaker and reasons.
- `app/services/recommendations.py`: loads candidates and signals in 4 queries.
- `GET /feed/recommended` for guests and signed-in readers (`cold_start` flag), paginated.
- UI: "For you" page with a reason on every card and hints for cold start.
