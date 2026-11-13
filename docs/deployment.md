# Deploying Aporia

Two ways to put Aporia on the internet:

- **[Render's free plan](#render-free-plan)**: one click, using the Blueprint in
  `render.yaml`. Costs nothing, but the site sleeps when nobody visits and the free
  database expires after 30 days.
- **[Your own server](#your-own-server-docker-compose)** with Docker Compose: the same
  stack as on your machine, behind HTTPS.

Both use only free software. The only external service you may want is an SMTP account
for email.

## Render (free plan)

`render.yaml` describes two resources, both on Render's free plan:

- a **web service** built from `deploy/Dockerfile`: one container in which nginx serves
  the app and forwards `/api` to the API, with the email worker running beside them
  (`deploy/start.sh` starts all three and applies migrations first);
- a **PostgreSQL 16 database** that only Render's private network can reach.

### Deploy

1. Sign up at [render.com](https://dashboard.render.com/register) (GitHub sign-in works).
   **Do not add a payment method.** Without one, Render suspends free services when a
   monthly allowance runs out instead of billing you.
2. Open <https://render.com/deploy?repo=https://github.com/IliyasNU/aporia>, check that
   both resources say _Free_ and click **Deploy Blueprint**. Leave the SMTP fields empty
   unless you already have an email provider (see [Email on Render](#email-on-render)).
3. The first build takes a few minutes. The address is on the service's page, for example
   `https://aporia.onrender.com` (or `aporia-xxxx` if the name is taken).
   `PUBLIC_BASE_URL` and `TRUSTED_ORIGINS` default to it (Render's `RENDER_EXTERNAL_URL`);
   set them yourself only for a custom domain.
4. **Become an administrator.** Sign up on the site first, then add `ADMIN_EMAIL` with
   that address under the service's _Environment_ and save. Every start of the service
   gives that account the admin role. Sign up first: whoever registers the address
   becomes the administrator.

From then on, every push to `main` deploys automatically once CI has passed on it
(`autoDeployTrigger: checksPass`).

### Email on Render

Free web services cannot connect to ports 25, 465 and 587, so use a provider that also
accepts SMTP on port **2525** with STARTTLS (Brevo, Mailgun, SendGrid and SMTP2GO do;
most have a free tier). Set `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD` and
`MAIL_FROM` (an address the provider lets you send from) under _Environment_;
`SMTP_PORT=2525` and `SMTP_STARTTLS=true` are already set.

Until `SMTP_HOST` is set, the site works normally but email subscriptions are switched
off: the form says they are not available yet (`503 email_unavailable`) and nothing is
queued.

### Free plan limits

From [Render's documentation](https://render.com/docs/free):

- The service **sleeps after 15 minutes without visitors**. The next visit wakes it in
  about a minute (Render shows a loading page). The email worker sleeps too, so emails
  queued in the meantime go out when it wakes.
- 750 free instance hours per workspace and month: enough for one service all month.
- 0.1 CPU and 512 MB RAM: signing in (Argon2id) takes a moment.
- **The free database expires 30 days after creation**, is deleted 14 days later and has
  no backups. Before then, upgrade it or [move the data](#moving-the-database) to another
  free PostgreSQL, such as a Neon project.
- No shell (hence `ADMIN_EMAIL`), and Render may restart free services at any time.

### Visitor addresses and rate limits

Rate limits count requests per visitor address, so the container must learn the real one.
On Render that is **`CF-Connecting-IP`** (`REAL_IP_HEADER` in `render.yaml`): Render's
`onrender.com` addresses sit behind Cloudflare, which sets that header to the visitor's
address and replaces any value a visitor sends. `X-Forwarded-For` does not work there:
tested on the live service, a spoofed value went through, and without one the last entry
is a changing proxy address, so the per-address limits never added up.

Elsewhere, set `REAL_IP_HEADER` to the header your load balancer sets (for example
`Fly-Client-IP` on Fly.io). The default, `X-Forwarded-For`, takes the last entry, which is
right for a proxy that appends the address it sees; CI checks that rule.

### Moving the database

1. Create the new database and copy its URL (a `postgresql://…?sslmode=require` URL from
   Neon works as is; the app adds the driver name itself).
2. In Render, allow your IP address under the old database's _Networking_ settings and
   copy its _External Database URL_.
3. Copy the data:

   ```bash
   pg_dump --format=custom --no-owner "$OLD_URL" > aporia.dump
   pg_restore --no-owner --dbname "$NEW_URL" aporia.dump
   ```

4. Set `DATABASE_URL` on the web service to the new URL and save. Remove your IP address
   from the old database.

The same external URL lets you run the maintenance commands from your machine, for
example `cd backend && DATABASE_URL="$OLD_URL" uv run python -m app.cli requeue-failed-emails`.

## Your own server (Docker Compose)

### What runs

| Service   | Image / command                     | Public?                       |
| --------- | ----------------------------------- | ----------------------------- |
| `web`     | nginx serving the SPA, proxy `/api` | **Yes**, behind HTTPS         |
| `api`     | `uvicorn app.main:app`              | No, only reachable from `web` |
| `worker`  | `python -m app.worker`              | No                            |
| `migrate` | `alembic upgrade head`, then exits  | No                            |
| `db`      | PostgreSQL 16                       | No                            |
| `mailpit` | development SMTP catcher            | **Do not run in production**  |

### Checklist

1. **A server** with Docker and the Compose plugin, and a domain name pointing to it.
2. **HTTPS in front of `web`** (SEC-04). The simplest option is [Caddy](https://caddyserver.com),
   which gets certificates automatically. Example `Caddyfile`:

   ```
   aporia.example.org {
       reverse_proxy 127.0.0.1:8080
       header Strict-Transport-Security "max-age=31536000"
   }
   ```

   **Client addresses and rate limits.** `web` (nginx) overwrites `X-Forwarded-For` with
   the address it sees. Behind Caddy that is the Docker gateway, so every visitor would
   share one rate-limit counter. Tell nginx to trust the proxy's header by adding to the
   `server` block of `frontend/nginx.conf` (adjust the range to your Docker network,
   `docker network inspect aporia_default`):

   ```
   set_real_ip_from 172.16.0.0/12;
   real_ip_header X-Forwarded-For;
   ```

3. **A `.env` file** next to `docker-compose.yml` (never commit it):

   ```
   APP_ENV=production
   SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(48))">
   POSTGRES_PASSWORD=<another long random value>
   PUBLIC_BASE_URL=https://aporia.example.org
   TRUSTED_ORIGINS=https://aporia.example.org
   SMTP_HOST=smtp.your-provider.example
   SMTP_PORT=587
   SMTP_USERNAME=...
   SMTP_PASSWORD=...
   SMTP_STARTTLS=true
   MAIL_FROM=Aporia <no-reply@aporia.example.org>
   ```

   With `APP_ENV=production` the API refuses to start without a real `SECRET_KEY`, and
   session cookies get the `Secure` flag (they then only work over HTTPS). Add
   `API_DOCS_ENABLED=false` if you do not want the Swagger UI page (it loads a pinned
   script from a CDN); the OpenAPI JSON stays available.

4. **Remove `mailpit`** from the stack (delete the service or run
   `docker compose up -d db migrate api worker web`).
5. **Keep the internal ports private.** The API port is not published at all (only
   nginx reaches it, which is what makes its `X-Forwarded-For` trustworthy); PostgreSQL
   (5432) and Mailpit (8025) are bound to `127.0.0.1`. Keep it that way.
6. **Start:** `docker compose up -d --build db migrate api worker web`.
7. **Create an administrator:** sign up in the browser, then
   `docker compose exec api python -m app.cli set-role you@example.org admin`.
8. **Check:** `curl https://aporia.example.org/api/v1/health` returns
   `{"status":"ok","database":"ok"}`; sign up, publish, subscribe with your own address.

### Updating

```bash
git pull
docker compose up -d --build db migrate api worker web
```

`migrate` applies new Alembic migrations before the API starts. Migrations only move
forward in production; take a backup first.

### Backups

The data lives in the `db-data` Docker volume. A daily logical backup:

```bash
docker compose exec -T db pg_dump -U aporia -Fc aporia > aporia-$(date +%F).dump
# restore into an empty database:
docker compose exec -T db pg_restore -U aporia -d aporia --clean < aporia-2026-01-01.dump
```

Keep backups somewhere else than the server, and test a restore once.

## Logs and data retention (SEC-06)

- Container logs are rotated by Docker (3 × 10 MB per service, see `x-logging`); Render
  keeps its own log history.
- They contain no passwords, session tokens, subscription links or subscriber addresses
  (SQL parameters are hidden and database error texts are not logged).
- The worker deletes finished email jobs after `EMAIL_JOB_RETENTION_DAYS` (90), unconfirmed
  subscriptions a week after their link expired, sessions a day after they ended, and
  deleted essays, comments and unsubscribed addresses after
  `DELETED_CONTENT_RETENTION_DAYS` (30).

## When email stops working

If SMTP credentials are wrong or a sending quota is used up, the worker keeps the emails
queued and retries (1, 5, 25, 125 minutes, up to 5 attempts). After fixing the cause,
emails that already gave up can be sent again:

```bash
docker compose exec api python -m app.cli requeue-failed-emails
```

On Render, run it from your machine with the database's external URL (see
[Moving the database](#moving-the-database)).

## Scaling notes

Aporia is built for one API process and one worker. Rate limits are kept in the API
process's memory: with several API processes each counts separately. Several workers are
safe (jobs are locked with `FOR UPDATE SKIP LOCKED`) but not needed.
