# Deploying Aporia

Aporia v1.0 has **not** been deployed publicly by the authors of this repository. This
guide describes how the owner can run it on a single server they control. It uses only
free software; the only external service you need is an SMTP account for email.

## What runs

| Service   | Image / command                     | Public?                       |
| --------- | ----------------------------------- | ----------------------------- |
| `web`     | nginx serving the SPA, proxy `/api` | **Yes**, behind HTTPS         |
| `api`     | `uvicorn app.main:app`              | No, only reachable from `web` |
| `worker`  | `python -m app.worker`              | No                            |
| `migrate` | `alembic upgrade head`, then exits  | No                            |
| `db`      | PostgreSQL 16                       | No                            |
| `mailpit` | development SMTP catcher            | **Do not run in production**  |

## Checklist

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
   session cookies get the `Secure` flag (they then only work over HTTPS).

4. **Remove `mailpit`** from the stack (delete the service or run
   `docker compose up -d db migrate api worker web`).
5. **Do not publish ports 5432, 8000 or 8025.** The compose file binds them to
   `127.0.0.1`, which keeps them off the internet; keep it that way.
6. **Start:** `docker compose up -d --build db migrate api worker web`.
7. **Create an administrator:** sign up in the browser, then
   `docker compose exec api python -m app.cli set-role you@example.org admin`.
8. **Check:** `curl https://aporia.example.org/api/v1/health` returns
   `{"status":"ok","database":"ok"}`; sign up, publish, subscribe with your own address.

## Updating

```bash
git pull
docker compose up -d --build db migrate api worker web
```

`migrate` applies new Alembic migrations before the API starts. Migrations only move
forward in production; take a backup first.

## Backups

The data lives in the `db-data` Docker volume. A daily logical backup:

```bash
docker compose exec -T db pg_dump -U aporia -Fc aporia > aporia-$(date +%F).dump
# restore into an empty database:
docker compose exec -T db pg_restore -U aporia -d aporia --clean < aporia-2026-01-01.dump
```

Keep backups somewhere else than the server, and test a restore once.

## Logs and data retention (SEC-06)

- Container logs are rotated by Docker (3 × 10 MB per service, see `x-logging`).
- They contain no passwords, session tokens, subscription links or subscriber addresses.
- The worker deletes finished email jobs after `EMAIL_JOB_RETENTION_DAYS` (90), unconfirmed
  subscriptions a week after their link expired, and sessions a day after they ended.

## Scaling notes

Aporia is built for one API process and one worker. Rate limits are kept in the API
process's memory: with several API processes each counts separately. Several workers are
safe (jobs are locked with `FOR UPDATE SKIP LOCKED`) but not needed.
