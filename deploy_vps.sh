#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_DIR}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Errore: docker non trovato nel PATH."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Errore: docker compose non disponibile."
  exit 1
fi

echo "==> Deploy MIO su VPS"
echo "==> Repo: ${PROJECT_DIR}"
echo "==> Commit locale prima del pull: $(git rev-parse --short HEAD)"

git fetch --all --prune
git pull --ff-only

echo "==> Commit attivo: $(git rev-parse --short HEAD)"
echo "==> Rebuild e restart container"
docker compose up -d --build

echo "==> Stato servizi"
docker compose ps

echo "==> Log recenti web"
docker compose logs --tail=80 web || true

echo "==> Log recenti mail_worker"
docker compose logs --tail=80 mail_worker || true

echo "==> Log recenti caddy"
docker compose logs --tail=80 caddy || true

echo "==> Deploy completato"
