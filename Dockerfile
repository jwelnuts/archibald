# syntax=docker/dockerfile:1.7

FROM node:22-slim AS frontend-build

WORKDIR /app

RUN corepack enable \
    && corepack prepare pnpm@10.6.0 --activate

COPY package.json pnpm-lock.yaml vite.config.mjs /app/
COPY core/static/core /app/core/static/core
COPY agenda/static/agenda /app/agenda/static/agenda
COPY subscriptions/static/subscriptions /app/subscriptions/static/subscriptions

RUN --mount=type=cache,id=mio-pnpm-store,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile \
    && pnpm build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /app/requirements.txt

COPY . /app
COPY --from=frontend-build /app/core/static/core/dist /app/core/static/core/dist

RUN chmod +x /app/docker/entrypoint.sh

EXPOSE 8000

CMD ["/app/docker/entrypoint.sh"]
