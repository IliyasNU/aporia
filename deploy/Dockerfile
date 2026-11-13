# Aporia in one container, for hosts that run one container per service (Render's
# free plan, see render.yaml): nginx serves the web app and forwards /api to uvicorn,
# and the email worker runs beside them. deploy/start.sh starts all three.
#
#   docker build -f deploy/Dockerfile -t aporia .     (from the repository root)
#
# docker-compose.yml, with one container per process, stays the way to run Aporia
# locally and on a server you control.

FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080

RUN apt-get update \
    && apt-get install --yes --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.11.32 \
    && useradd --create-home --uid 1000 aporia

WORKDIR /app

# Dependencies first, so code changes do not invalidate this layer.
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --locked --no-dev --no-cache

COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/app ./app

# The same nginx site as the "web" container (security headers, CSP, body limit),
# with the API on localhost instead of the "api" Compose service. The build fails
# if that line ever changes in frontend/nginx.conf.
COPY frontend/nginx.conf /etc/nginx/aporia-site.conf
RUN sed -i 's#proxy_pass http://api:8000;#proxy_pass http://127.0.0.1:8000;#' /etc/nginx/aporia-site.conf \
    && grep -q 'proxy_pass http://127.0.0.1:8000;' /etc/nginx/aporia-site.conf \
    && grep -q 'listen 8080;' /etc/nginx/aporia-site.conf \
    && rm -rf /usr/share/nginx/html
COPY --from=web /web/dist /usr/share/nginx/html
COPY deploy/nginx.conf deploy/start.sh /app/deploy/

USER aporia
EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=3s --start-period=30s --retries=3 \
    CMD ["sh", "-c", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:${PORT}/api/v1/health', timeout=2)\""]

CMD ["bash", "/app/deploy/start.sh"]
