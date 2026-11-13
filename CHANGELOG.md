# Changelog

## v1.0.0: release candidate (not yet merged)

The first complete version of Aporia, built in seven stacked pull requests
(Stage 0 to Stage 7).

### Features

- Accounts: sign up, sign in and out with server-side sessions; profile; topic interests.
- Publishing: Markdown essays with drafts, preview, publish/unpublish, soft delete, stable
  links, tags (curated catalog), search, tag/author filters, latest or most-saved order.
- Reading: home, essay, author and personal-area pages; works at 360 px.
- Community: follow authors with a Following feed, save essays, flat comments.
- Moderation: reports; admins hide or unhide essays and comments; permanent removal and
  account deletion through `python -m app.cli`.
- Email: double opt-in subscriptions to an author without an account; one email per new
  essay through a separate worker with retries; unsubscribe link in every email.
- Recommendations: transparent formula (interests, follows, saves, freshness, diversity)
  with a reason for every essay and a cold start for guests.
- Operations: Docker Compose (db, migrate, api, worker, web, Mailpit), GitHub Actions
  (lint, types, tests, Compose smoke and end-to-end email chain), demo data command.

### Security

Argon2id, hashed session and email tokens, `HttpOnly`/`SameSite=Lax`/`Secure` cookies,
Origin/Referer CSRF check, rate limits, request size limits, safe Markdown rendering,
Content-Security-Policy and other headers, no secrets in logs. See `docs/security.md`.

### Independent audit

An independent pre-release audit found 4 medium and 11 low issues plus notes; all were
fixed or consciously accepted before release. See `docs/audit-v1.0.md`.

### Known limitations

- Rate limits are kept in memory per API process (fine for the single-process setup).
- Search is a case-insensitive substring match, not full-text search.
- Recommendations consider the newest 300 public essays.
- Email delivery is at-least-once: a worker crash right after sending can cause one
  duplicate (documented in the README).
- Registration reveals whether an email already has an account (no email verification
  for accounts in v1.0); login does not.
- No self-service account deletion, password reset, OAuth, image uploads, comment replies,
  notifications or admin panel; these are v1.1+ per the requirements.
- No server-side rendering or sitemap (optional in the spec).
- Creating an essay reveals whether its title's slug is already taken (also by drafts).
- Ten failed logins for one email in five minutes block that email for up to five
  minutes, including its owner.
- Not deployed publicly; `docs/deployment.md` explains how.
