# A 5–7 minute demo

Everything runs locally; no accounts, keys or paid services.

## Prepare (before the audience arrives)

```bash
docker compose up --build -d --wait
docker compose exec api python -m app.cli seed-demo
```

`seed-demo` creates clearly labelled demo data (handles `demo_*`, names "Demo · …", essays
titled "Demo: …"): three authors, six essays, and a reader `demo_reader@example.com` with
password `demo-password`, who is interested in Ethics and Logic and follows Marcus. It
refuses to run with `APP_ENV=production`.

Open three tabs: http://localhost:8080 (signed out), a private window, and
http://localhost:8025 (Mailpit).

## Script

1. **Reading without an account (1 min).** On the home page, search "attention", click
   the _Stoicism_ tag, sort by _Most saved_. Open an essay: Markdown, author, tags.
2. **Explainable recommendations (1 min).** Open _For you_ as a guest: "Recently
   published" / "Popular with readers". Sign in as `demo_reader`: the reasons change to
   "You are interested in Ethics" and "You follow Demo · Marcus".
3. **Writing (1.5 min).** In the private window, sign up. Pick interests in the account
   page. _Write_: title, tags, Markdown, _Preview_, _Save draft_. Show that the draft URL
   gives "does not exist" in the other window. _Publish_, then rename it: the URL stays.
4. **Email subscription (1.5 min).** As a guest, open the new author's profile and
   subscribe with any address. In Mailpit: the confirmation email. Open the link, press
   _Confirm_. Publish a second essay as the author; within seconds Mailpit shows "New essay
   by …" with an unsubscribe link. Edit the essay: no second email.
5. **Community and moderation (1 min).** As `demo_reader`: _Save_, _Follow_, comment, and
   _Report_ a comment. Then make someone an admin and hide it:

   ```bash
   docker compose exec api python -m app.cli set-role demo_ada@example.com admin
   ```

   Sign in as `demo_ada` (password `demo-password`), open http://localhost:8080/api/v1/docs,
   call `GET /admin/reports` and `POST /admin/moderate`: the comment disappears.

6. **Wrap-up (30 s).** Point at the Swagger docs, the green CI run and the README's
   verification table.

## Reset

```bash
docker compose down --volumes   # deletes all data, including the demo
```
