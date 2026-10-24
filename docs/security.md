# Security and privacy overview

How Aporia v1.0 meets the security requirements (SEC-01 … SEC-07), and where to look in
the code. Tests named here run in CI.

| Requirement                                                                 | How                                                                                                                                                                                   | Where                                                                                  | Tested by                                                                                                                              |
| --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **SEC-01** Authorization on every mutating API; owner checks; admin by role | `CurrentUser` dependency, `get_own_*` helpers, `require_admin`                                                                                                                        | `app/api/deps.py`, `app/services/*`, `app/services/moderation.py`                      | `test_security.py` (every POST/PUT/PATCH/DELETE without a session → 401), `test_articles.py`, `test_comments.py`, `test_moderation.py` |
| **SEC-02** No executable HTML from users                                    | API stores raw text; React renders Markdown with `skipHtml`, safe URL filter, no images; comments as plain text; CSP `script-src 'self'`                                              | `frontend/src/components/Markdown.tsx`, `frontend/nginx.conf`                          | `Markdown.test.tsx`, browser check for CSP violations                                                                                  |
| **SEC-03** Rate limits; body and field limits                               | per IP/email/user sliding windows; 413 above 512 KB; Pydantic length limits                                                                                                           | `app/core/rate_limit.py`, `app/main.py`, `app/schemas/*`                               | `test_security.py`, validation tests per feature                                                                                       |
| **SEC-04** Cookies, CSRF, CORS, HTTPS                                       | `HttpOnly`, `SameSite=Lax`, `Secure` in production; Origin/Referer check; no CORS (same origin); HTTPS via reverse proxy                                                              | `app/api/deps.py`, `app/core/csrf.py`, `docs/deployment.md`                            | `test_auth.py`, `test_csrf.py`                                                                                                         |
| **SEC-05** No secrets in logs or public answers                             | only IDs are logged; `SecretStr` settings; tokens in URL fragments; subscriber addresses never returned                                                                               | `app/core/config.py`, `app/services/newsletter.py`, `app/worker/email_jobs.py`         | log-capture tests in `test_auth.py`, `test_newsletter.py`, `test_email_worker.py`                                                      |
| **SEC-06** Data policy                                                      | minimal fields; retention cleanup (jobs 90 d, unconfirmed subscriptions, ended sessions); unsubscribe in every email; Docker log rotation; privacy notice and publication rules pages | `app/worker/email_jobs.py`, `docker-compose.yml`, `frontend/src/pages/PolicyPages.tsx` | `test_email_worker.py`, `test_maintenance.py`, `PolicyPages.test.tsx`                                                                  |
| **SEC-07** Abuse handling                                                   | reports, admin hide/unhide, manual permanent deletion commands                                                                                                                        | `app/services/moderation.py`, `app/cli.py`, README "Moderation"                        | `test_moderation.py`, `test_maintenance.py`                                                                                            |

## Accounts and sessions

- Argon2id password hashes (upgraded on login when parameters change).
- Session cookie = random 256-bit token; the database stores its SHA-256. Logout revokes
  it; expired, revoked or tampered cookies get 401. Signing in again replaces the old
  session.
- Login answers identically for unknown emails and wrong passwords, with similar timing.
  Registration does reveal that an email is taken (avoiding that needs email
  verification, which is outside v1.0); rate limits slow down probing.

## Email

- Double opt-in; the subscribe endpoint answers identically for every address and sends at
  most one confirmation per address per 10 minutes, plus a per-IP limit.
- Confirmation tokens: random, 48-hour TTL, stored hashed, single purpose. Unsubscribe
  tokens: `HMAC(SECRET_KEY, subscription id)`, stored hashed.
- Email subjects are cleaned of newlines (no header injection).

## Browser protections (nginx)

`Content-Security-Policy` (scripts, styles, connections only from the site; no framing;
no plugins), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`,
`Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, and no version
in the `Server` header.

## Known limits

- Rate-limit counters live in the API process's memory (one process in this setup).
- The API trusts `X-Forwarded-For` from any address (`FORWARDED_ALLOW_IPS="*"`); that is
  safe only because Docker Compose does not publish its port. Never add one.
- Swagger UI (`/api/v1/docs`) loads a pinned version from a CDN; set
  `API_DOCS_ENABLED=false` to switch it off.
- Creating an essay reveals whether its slug is already taken (even by a draft): the
  title's slug is visible, never the content.
- Ten failed logins for one email within five minutes block further attempts for that
  email, including its owner, until the window passes.
- No account self-deletion in v1.0; the operator uses `python -m app.cli delete-user`.
- No two-factor authentication or password reset (v1.1+ per the requirements).

The independent pre-release audit and how each finding was resolved:
[audit-v1.0.md](audit-v1.0.md).
