# Author: Pradeep Sahoo — Retail Nexus AI
# syntax=docker/dockerfile:1.7

# ---------- Stage 1: dependencies ----------
FROM node:25-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm \
    if [ -f package-lock.json ]; then npm ci; else npm install --no-audit --no-fund; fi

# ---------- Stage 2: build ----------
FROM node:25-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NODE_ENV=production
RUN npm run build

# ---------- Stage 3: production runtime (nginx) ----------
FROM nginx:1.27-alpine AS runtime

ENV PORT=8080

# Non-root hardening + healthcheck tooling.
RUN apk add --no-cache curl \
 && addgroup -S -g 1001 app \
 && adduser -S -u 1001 -G app app \
 && mkdir -p /var/cache/nginx /var/run /var/log/nginx \
 && chown -R app:app /var/cache/nginx /var/run /var/log/nginx /usr/share/nginx/html

COPY --chown=app:app nginx.conf /etc/nginx/nginx.conf
COPY --from=build --chown=app:app /app/dist /usr/share/nginx/html

USER app
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail --silent --show-error http://127.0.0.1:${PORT}/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]

# ---------- Stage 4: dev runtime (Vite) ----------
FROM node:25-alpine AS dev
WORKDIR /app
RUN addgroup -S -g 1001 app \
 && adduser -S -u 1001 -G app app \
 && chown -R app:app /app
USER app
COPY --from=deps --chown=app:app /app/node_modules ./node_modules
COPY --chown=app:app . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
