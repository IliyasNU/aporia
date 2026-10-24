# Release checklist: v1.0

Each mandatory scenario from the requirements (section 10) and each Definition of Done item
(section 12), with the evidence. **Automatic** means it runs in CI on every push;
**Manual** means it was checked by hand (in a browser or against the running stack) and is
not repeated automatically.

## Mandatory end-to-end scenarios

| #   | Scenario                                                                                                        | Evidence                                                                                                                                                | How                |
| --- | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| 1   | Register → log in → session kept → log out → old cookie refused                                                 | `test_auth.py::test_logout_revokes_session_and_old_cookie_cannot_be_reused`, login and session tests                                                    | Automatic          |
| 2   | A guest opens a published essay but not someone's draft, even knowing its id                                    | `test_articles.py::test_draft_is_visible_only_to_its_author`, `test_published_article_is_public`                                                        | Automatic          |
| 3   | Author creates a draft, publishes, changes the title; the old public slug still works                           | `test_articles.py::test_slug_is_frozen_after_first_publication`                                                                                         | Automatic          |
| 4   | Another user cannot update, unpublish or delete an author's essay or comment                                    | `test_articles.py::test_stranger_cannot_change_someone_elses_article`, `test_comments.py::test_nobody_else_can_edit_or_delete_a_comment`                | Automatic          |
| 5   | Follow/unfollow and bookmarks are idempotent; unique constraints prevent duplicates                             | `test_social.py` (idempotency and row counts)                                                                                                           | Automatic          |
| 6   | Search and tags handle pagination, empty results, bad parameters and Unicode                                    | `test_catalog.py`                                                                                                                                       | Automatic          |
| 7   | Email subscription starts pending; a wrong or expired token confirms nothing                                    | `test_newsletter.py`                                                                                                                                    | Automatic          |
| 8   | One publication creates one job per active subscription; editing creates none                                   | `test_newsletter.py::test_first_publication_queues_one_job_per_confirmed_subscriber`, `test_edits_and_republishing_never_queue_again`                   | Automatic          |
| 9   | After unsubscribe no new jobs; a running worker respects the cancellation                                       | `test_newsletter.py`, `test_email_worker.py::test_unsubscribing_before_sending_cancels_the_job`                                                         | Automatic          |
| 10  | SMTP down: publication succeeds, job retries, error in logs without address or token                            | `test_email_worker.py` (retry, give up, log content), `test_publication_succeeds_even_if_smtp_is_down`; Mailpit stopped and restarted on the real stack | Automatic + Manual |
| 11  | Cold-start and personal recommendations are stable and contain no deleted/hidden essays                         | `test_ranking.py`, `test_recommendations.py`                                                                                                            | Automatic          |
| 12  | An admin hides a comment; readers no longer see it; ordinary users get no admin rights                          | `test_moderation.py`; three-user browser run                                                                                                            | Automatic + Manual |
| 13  | Clean Docker Compose with migrations → registration → essay → subscription → email in Mailpit → recommendations | CI smoke job: `docker compose up --build --wait` + `scripts/e2e_smoke.py`                                                                               | Automatic          |
| 14  | Frontend at 360 px, keyboard navigation, visible loading/error states                                           | Vitest page tests for states; Chromium runs at 360 px (no horizontal scroll, skip link first, focus outlines)                                           | Automatic + Manual |

## Definition of Done

| Item                                                                                         | Status                                                                                                |
| -------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Every MVP requirement ID implemented, or the gap stated                                      | Done: see `docs/roadmap.md`; no gaps. Optional items not done: SSR and sitemap (allowed by the spec). |
| Installation from the README works without personal secrets (local demo)                     | Done: `docker compose up --build` uses only defaults; CI does exactly this                            |
| Functionality uses the real PostgreSQL, not JSON files or frontend mocks                     | Done: every screen calls the API; frontend mocks exist only in unit tests                             |
| All public APIs documented in OpenAPI; auth, permissions and errors checked                  | Done: `/api/v1/docs`; every route lists its error responses; `test_security.py`                       |
| Frontend fully working: no empty buttons or fake counters                                    | Done: every control calls the API (checked by the browser runs)                                       |
| Email double opt-in and unsubscribe work with local SMTP capture; production SMTP documented | Done: Mailpit + `scripts/e2e_smoke.py`; `docs/deployment.md`                                          |
| Recommendations reproducible, explainable, no unpublished content                            | Done: pure function + tests with fixed inputs; reasons on every item                                  |
| Migrations apply to a clean DB and on update; data survives a normal restart                 | Done: CI migrates from empty; `test_migrations.py` up/down; restart checked manually                  |
| CI on the commit proposed for release; Docker images build                                   | Done: GitHub Actions on every push; the smoke job builds all images                                   |
| No secrets in the repository, logs, reports or UI                                            | Done: `.env` ignored; placeholders only; log tests                                                    |
| A short 5–7 minute demo and a list of known limitations                                      | Done: `docs/demo.md`, `CHANGELOG.md` (known limitations)                                              |
| The owner reviews the final diff and decides on merge/release                                | **Pending: owner**                                                                                    |
