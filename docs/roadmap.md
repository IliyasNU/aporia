# Roadmap (v1.0 MVP)

Each stage is a separate pull request into `main`. Nothing is merged without the
owner's approval. Requirement IDs refer to the v1.0 product requirements.

| Stage | Scope                                                         | Requirements              | Status        |
| ----- | ------------------------------------------------------------- | ------------------------- | ------------- |
| 0     | Foundation: repo layout, settings, Compose, migrations, CI    | —                         | **In review** |
| 1     | Accounts: register/login/logout, sessions, profile, interests | AUTH-01, AUTH-02, USER-01 | **In review** |
| 2     | Publishing: articles, drafts, tags, search, public API        | ART-01, ART-02, ART-03    | Not started   |
| 3     | Frontend: public pages, profiles, editor, personal area       | FE-01 … FE-05             | Not started   |
| 4     | Social: follows, bookmarks, comments, moderation              | SOC-01, SOC-02, MOD-01    | Not started   |
| 5     | Email: double opt-in, unsubscribe, DB-backed jobs, worker     | MAIL-01 … MAIL-04, FE-07  | Not started   |
| 6     | Recommendations: heuristic ranker, cold start, reasons        | REC-01 … REC-03, FE-06    | Not started   |
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
- Not yet: rate limiting (Stage 7), the web UI for these features (Stage 3), the author's
  article list on the public profile (Stage 2), admin assignment (Stage 4).
