#!/usr/bin/env sh
set -e

python manage.py migrate --noinput
python manage.py sync_radicale_users

STYLE_MODE="${UI_STYLE_MODE:-}"
if [ -z "$STYLE_MODE" ]; then
  case "${LESS_DEV_MODE:-}" in
    1|true|TRUE|yes|YES|on|ON) STYLE_MODE="DEV" ;;
    *) STYLE_MODE="PROD" ;;
  esac
fi

if [ "$STYLE_MODE" = "PROD" ]; then
  python manage.py compile_less --quiet --minify
else
  python manage.py compile_less --quiet
fi

python manage.py collectstatic --noinput

exec gunicorn mio_master.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-120}"
