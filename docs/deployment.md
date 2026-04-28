---
title: Deployment
tags: [deployment, docker, server]
aliases: [docker, vps, production]
---

# Deployment

This document describes Docker and deployment configuration for MIO Master.

---

## Docker Compose Stack

### Services

| Service | Description | Port |
|---------|-------------|------|
| `web` | Django + Gunicorn | 8000 |
| `mail_worker` | Archibald inbox worker | - |
| `db` | PostgreSQL 16 | 5432 |
| `radicale` | CalDAV/CardDAV server | 5232 |
| `caddy` | Reverse proxy + HTTPS | 80/443 |

### Architecture
```
Internet → Caddy (HTTPS) → Django (web)
                  ↳ Static/Media

Caddy → PostgreSQL (db)
```

---

## Quick Start (Local Development)

```bash
# Clone and setup
cd mio_master
cp .env.local.example .env

# Start with Docker
docker compose up -d --build

# Create superuser
docker compose exec web python manage.py createsuperuser

# Open browser
http://127.0.0.1/
```

---

## Environment Variables

### Required
| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Django secret key |
| `DJANGO_DEBUG` | false (production) |
| `UI_STYLE_MODE` | DEV/PROD |
| `DATABASE_URL` | PostgreSQL URL |
| `DJANGO_ALLOWED_HOSTS` | Allowed hosts |

### Optional - AI Features
| Variable | Default |
|----------|---------|
| `OPENAI_API_KEY` | - |
| `OPENAI_MODEL` | gpt-4o-mini |
| `OPENAI_MODEL_ARCHIBALD` | gpt-5-mini |

### Optional - Email
| Variable | Description |
|----------|-------------|
| `ARCHIBALD_MAIL_IMAP_HOST` | IMAP server |
| `ARCHIBALD_MAIL_SMTP_HOST` | SMTP server |
| `ARCHIBALD_MAIL_DEFAULT_INBOX` | Default inbox |

### Optional - CalDAV
| Variable | Description |
|----------|-------------|
| `CALDAV_ENABLED` | Enable CalDAV |
| `CALDAV_BASE_URL` | Radicale URL |
| `CALDAV_LOGIN_DOMAIN` | Login domain |

### Optional - Vault
| Variable | Description |
|----------|-------------|
| `VAULT_ENCRYPTION_KEY` | Encryption key |
| `VAULT_SESSION_TIMEOUT_SECONDS` | 600 |

---

## Management Commands

### Archibald Mail Worker

```bash
# Process inbox manually
python manage.py process_archibald_inbox

# Send notifications
python manage.py send_archibald_notifications

# Run continuous worker
python manage.py run_archibald_mail_worker --interval-seconds 300

# Options
--run-once          # Single cycle
--user <email>     # Limit to user
--force            # Ignore is_enabled
--disable-archi-fast # Disable fast lane
```

### Cron Setup

```bash
# Process inbox every 5 minutes
*/5 * * * * cd /path/mio_master && .venv/bin/python manage.py process_archibald_inbox >> /var/log/mio_archibald_mail.log 2>&1

# Notifications every 15 minutes
*/15 * * * * cd /path/mio_master && .venv/bin/python manage.py send_archibald_notifications >> /var/log/mio_archibald_notify.log 2>&1
```

---

## Security Notes

### Authentication
- Login required on most views
- Vault requires TOTP + session timeout
- Mobile API uses token hashing (SHA256)

### Vault Encryption
- Uses `cryptography.Fernet`
- Key derived from `VAULT_ENCRYPTION_KEY` or `SECRET_KEY`

### Media Files
- Protected via `/media/<path>` endpoint
- Ownership check before serving

### Superuser Tools
- Workbench routes restricted to superuser

---

## Frontend Build

### Requirements
```bash
pnpm install --frozen-lockfile
pnpm build
```

### Dev Mode
```bash
pnpm dev   # Watch mode
```

### Style Modes
| Mode | Description |
|------|-------------|
| `DEV` | Compile LESS on each request |
| `PROD` | Use pre-compiled CSS |

---

## Related Documentation

- [[index|Main Index]]
- [[apps|Apps Overview]]
- [[models|Database Models]]
- [[business-logic|Business Logic]]

---

## External Resources

- [GitHub Repository](https://github.com/anomalyco/mio_master)
- [README](../README.md) - Full technical README
- [[caldav-unification|CalDAV Integration]]