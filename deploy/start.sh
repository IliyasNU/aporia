#!/bin/bash
# Entry point of the single-container image (deploy/Dockerfile): applies migrations,
# then runs the API, the email worker and nginx side by side. When one of them stops,
# the others are stopped too and the container exits, so the host restarts it.
set -euo pipefail

# Render tells the service its public address; elsewhere set PUBLIC_BASE_URL.
export PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-${RENDER_EXTERNAL_URL:-http://localhost:$PORT}}"
export TRUSTED_ORIGINS="${TRUSTED_ORIGINS:-$PUBLIC_BASE_URL}"
# Without an SMTP account the site still works; only email subscriptions are off.
if [ -z "${SMTP_HOST:-}" ]; then
    export EMAIL_ENABLED="${EMAIL_ENABLED:-false}"
fi

# The header that carries the visitor's address from the host's load balancer.
REAL_IP_HEADER="${REAL_IP_HEADER:-X-Forwarded-For}"
if [[ ! "$REAL_IP_HEADER" =~ ^[A-Za-z0-9-]+$ ]]; then
    echo "REAL_IP_HEADER must be an HTTP header name" >&2
    exit 1
fi
if [[ ! "$PORT" =~ ^[0-9]+$ ]]; then
    echo "PORT must be a number" >&2
    exit 1
fi
mkdir -p /tmp/nginx
sed "s/@REAL_IP_HEADER@/$REAL_IP_HEADER/" /app/deploy/nginx.conf > /tmp/nginx/nginx.conf
sed "s/listen 8080;/listen $PORT;/" /etc/nginx/aporia-site.conf > /tmp/nginx/site.conf

# The database may still be starting (or waking up) when the container starts.
for attempt in 1 2 3 4 5; do
    alembic upgrade head && break
    if [ "$attempt" = 5 ]; then exit 1; fi
    sleep 5
done

# Hosts without a shell (Render's free plan) cannot run `python -m app.cli set-role`.
# ADMIN_EMAIL makes that account an administrator on every start. Sign up first:
# whoever registers the address becomes the administrator.
if [ -n "${ADMIN_EMAIL:-}" ]; then
    python -m app.cli set-role "$ADMIN_EMAIL" admin 2> /dev/null \
        || echo "ADMIN_EMAIL: no account with that address yet; sign up, then restart" >&2
fi

pids=()
uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers &
pids+=($!)
python -m app.worker &
pids+=($!)
nginx -c /tmp/nginx/nginx.conf -e stderr -g "daemon off;" &
pids+=($!)

stop() { kill -TERM "${pids[@]}" 2> /dev/null || true; }
trap stop TERM INT

# Wait until any process exits (or the host asks the container to stop) ...
status=0
wait -n || status=$?
# ... then stop the others and leave with the first exit status.
stop
wait || true
exit "$status"
