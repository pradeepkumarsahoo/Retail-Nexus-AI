# Author: Pradeep Sahoo — Retail Nexus AI
# syntax=docker/dockerfile:1.7

# ---------- Stage 1: builder ----------
FROM python:3.15-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --prefix=/install --no-warn-script-location -r requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.15-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

# Runtime system deps only (libpq for psycopg, curl for healthcheck, tini as PID 1).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tini \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 1001 app \
 && useradd  --system --uid 1001 --gid app --home ${APP_HOME} --shell /usr/sbin/nologin app

# Copy pre-built wheels / installed packages from the builder stage.
COPY --from=builder /install /usr/local

# Copy application source. Non-source files are filtered via .dockerignore.
COPY --chown=app:app . ${APP_HOME}

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail --silent --show-error http://127.0.0.1:${PORT}/healthz || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
