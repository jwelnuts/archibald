#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Uso: ./deploy_vps.sh [opzioni]

Opzioni:
  --branch <nome>   Branch da deployare (default: branch corrente)
  --autostash       Se il working tree e sporco, crea stash temporaneo e lo ripristina
  --force-sync      Allinea forzatamente il repo a origin/<branch> e pulisce file untracked (tranne .env)
  --skip-checks     Salta i check post-deploy (manage.py check + sync_radicale_users)
  -h, --help        Mostra questo aiuto
EOF
}

AUTOSTASH=0
FORCE_SYNC=0
SKIP_CHECKS=0
BRANCH=""
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --branch)
      shift
      if [[ "${1:-}" == "" ]]; then
        echo "Errore: --branch richiede un valore."
        exit 1
      fi
      BRANCH="$1"
      ;;
    --autostash)
      AUTOSTASH=1
      ;;
    --force-sync)
      FORCE_SYNC=1
      ;;
    --skip-checks)
      SKIP_CHECKS=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Opzione non valida: $1"
      usage
      exit 1
      ;;
  esac
  shift
done

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_DIR}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Errore: ${PROJECT_DIR} non e una repository git."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Errore: docker non trovato nel PATH."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Errore: docker compose non disponibile."
  exit 1
fi

if [[ ! -f ".env" ]]; then
  echo "Errore: file .env non trovato in ${PROJECT_DIR}."
  echo "Crea .env partendo da .env.vps.example prima del deploy."
  exit 1
fi

ENV_BACKUP="$(mktemp "${TMPDIR:-/tmp}/mio_env_backup.XXXXXX")"
cp ".env" "${ENV_BACKUP}"
chmod --reference=".env" "${ENV_BACKUP}" 2>/dev/null || true

restore_env_if_needed() {
  if [[ -f "${ENV_BACKUP}" ]]; then
    if [[ ! -f ".env" ]] || ! cmp -s "${ENV_BACKUP}" ".env"; then
      cp "${ENV_BACKUP}" ".env"
      chmod --reference="${ENV_BACKUP}" ".env" 2>/dev/null || true
      echo "==> .env ripristinato dal backup locale"
    fi
    rm -f "${ENV_BACKUP}"
  fi
}
trap restore_env_if_needed EXIT

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
TARGET_BRANCH="${BRANCH:-${CURRENT_BRANCH}}"

echo "==> Deploy MIO su VPS"
echo "==> Repo: ${PROJECT_DIR}"
echo "==> Branch target: ${TARGET_BRANCH}"
echo "==> Commit locale prima del sync: $(git rev-parse --short HEAD)"
if [[ "${FORCE_SYNC}" -eq 1 ]]; then
  echo "==> Modalita force-sync attiva (reset hard + clean untracked, .env preservato)"
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

echo "==> Fetch remoto"
git fetch origin --prune

if ! git show-ref --verify --quiet "refs/remotes/origin/${TARGET_BRANCH}"; then
  echo "Errore: branch remota origin/${TARGET_BRANCH} non trovata."
  exit 1
fi

if [[ "$(git rev-parse --abbrev-ref HEAD)" != "${TARGET_BRANCH}" ]]; then
  if git show-ref --verify --quiet "refs/heads/${TARGET_BRANCH}"; then
    git checkout "${TARGET_BRANCH}"
  else
    git checkout -b "${TARGET_BRANCH}" "origin/${TARGET_BRANCH}"
  fi
fi

if [[ "${FORCE_SYNC}" -eq 1 ]]; then
  echo "==> Forzo allineamento a origin/${TARGET_BRANCH}"
  git reset --hard "origin/${TARGET_BRANCH}"
  git clean -fd -e .env
else
  echo "==> Pull fast-forward da origin/${TARGET_BRANCH}"
  git pull --ff-only origin "${TARGET_BRANCH}"
fi

if [[ "${STASHED}" -eq 1 ]]; then
  echo "==> Ripristino stash temporaneo"
  if ! git stash pop; then
    echo "Errore: conflitto durante il ripristino stash. Risolvi i conflitti e rilancia il deploy."
    exit 1
  fi
fi

echo "==> Commit attivo: $(git rev-parse --short HEAD)"
echo "==> Verifica configurazione compose"
docker compose config -q

echo "==> Rebuild e restart container"
docker compose up -d --build --wait --wait-timeout 240

echo "==> Stato servizi"
docker compose ps

if [[ "${SKIP_CHECKS}" -eq 0 ]]; then
  echo "==> Django check"
  docker compose exec -T web python manage.py check

  echo "==> Sync utenti Radicale"
  docker compose exec -T web python manage.py sync_radicale_users
fi

echo "==> Log recenti web"
docker compose logs --tail=80 web || true

echo "==> Log recenti mail_worker"
docker compose logs --tail=80 mail_worker || true

echo "==> Log recenti caddy"
docker compose logs --tail=80 caddy || true

echo "==> Log recenti radicale"
docker compose logs --tail=80 radicale || true

echo "==> Deploy completato"
