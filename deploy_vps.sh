#!/usr/bin/env bash
set -euo pipefail

AUTOSTASH=0
FORCE_SYNC=0
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --autostash)
      AUTOSTASH=1
      ;;
    --force-sync)
      FORCE_SYNC=1
      ;;
    *)
      echo "Uso: $0 [--autostash] [--force-sync]"
      exit 1
      ;;
  esac
  shift
done

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
if [[ "${FORCE_SYNC}" -eq 1 ]]; then
  echo "==> Modalita force-sync attiva (reset hard dei file tracciati prima del deploy)"
fi

STASHED=0
if [[ "${FORCE_SYNC}" -ne 1 && -n "$(git status --porcelain)" ]]; then
  if [[ "${AUTOSTASH}" -ne 1 ]]; then
    echo "Errore: working tree sporco. Pull bloccato per evitare overwrite."
    git status --short
    echo "Suggerimento: riesegui con --autostash oppure fai commit/stash manuale."
    exit 1
  fi

  STASH_NAME="deploy_vps_autostash_$(date +%Y%m%d_%H%M%S)"
  echo "==> Working tree sporco: salvo stash temporaneo (${STASH_NAME})"
  git stash push --include-untracked -m "${STASH_NAME}"
  STASHED=1
fi

git fetch --all --prune
if [[ "${FORCE_SYNC}" -eq 1 ]]; then
  UPSTREAM="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
  if [[ -z "${UPSTREAM}" ]]; then
    UPSTREAM="origin/main"
  fi
  echo "==> Forzo allineamento a ${UPSTREAM}"
  git reset --hard "${UPSTREAM}"
else
  git pull --ff-only
fi

if [[ "${STASHED}" -eq 1 ]]; then
  echo "==> Ripristino stash temporaneo"
  if ! git stash pop; then
    echo "Errore: conflitto durante il ripristino stash. Risolvi i conflitti e rilancia il deploy."
    exit 1
  fi
fi

echo "==> Commit attivo: $(git rev-parse --short HEAD)"
echo "==> Rebuild e restart container"
docker compose up -d --build --wait --wait-timeout 180

echo "==> Stato servizi"
docker compose ps

echo "==> Log recenti web"
docker compose logs --tail=80 web || true

echo "==> Log recenti mail_worker"
docker compose logs --tail=80 mail_worker || true

echo "==> Log recenti caddy"
docker compose logs --tail=80 caddy || true

echo "==> Log recenti radicale"
docker compose logs --tail=80 radicale || true

echo "==> Deploy completato"
