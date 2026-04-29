#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_DIR}"

echo "==> pnpm build"
pnpm build

echo "==> collectstatic"
python manage.py collectstatic --noinput --clear

echo "==> runserver"
python manage.py runserver
