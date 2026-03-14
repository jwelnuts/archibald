# MIO Master (archibald)

Snapshot documentazione: 27 febbraio 2026

Monolite Django per organizzazione personale: finanza, progetti, planner/todo/routine, knowledge link, vault cifrato e assistente AI (Archibald), con workspace tecnico (Workbench) per debug e generazione guidata.

## Stato attuale (snapshot)

- Backend: Django `6.0.1` con app multi-modulo e ownership per utente (`OwnedModel`).
- DB: SQLite in locale (`db.sqlite3`) + PostgreSQL in produzione via `DATABASE_URL`.
- Deploy: VPS con Docker Compose (Django + Postgres + Caddy).
- AI: integrazione OpenAI Responses API per Archibald e generatori Workbench.
- Sicurezza: login richiesto su quasi tutte le viste, Vault con TOTP + cifratura contenuti.

## Stack tecnico

- Python 3.12.x
- Django 6.0.1
- Gunicorn 23.0.0
- Whitenoise 6.9.0
- dj-database-url 3.0.1
- psycopg 3.2.13
- cryptography 44.0.1
- pyotp 2.9.0
- qrcode 8.2

### Frontend (runtime UI)

- UIKit (static locale in `core/static/core/vendor/uikit`)
- HTMX (static locale in `core/static/core/vendor/htmx`)
- Stimulus (bootstrap in `core/static/core/stimulus.js`)
- UIKit baseline bridge (`core/static/core/uikit_bridge.js`)

Note Stimulus:

- l'app Stimulus viene avviata globalmente da `core/static/core/app.js`
- i controller vengono registrati tramite helper in `core/static/core/stimulus.js`
- il modulo `routines` e gia migrato a controller Stimulus (`data-controller="routines"`)
- al momento il modulo Stimulus viene importato via ESM URL (`unpkg`) in `core/static/core/stimulus.js`

## Moduli applicativi

### Core (`/`)
- Autenticazione (`/accounts/*`), signup, logout, profilo.
- Dashboard base.
- Endpoint calendario aggregato (`/calendar/events`) con eventi da:
  - todo
  - planner
  - subscriptions
  - transactions
  - routines
- Gestione account finanziari (`/core/accounts/*`).
- Configurazione hero actions globali utente.

### Finanza
- `finance_hub` (`/finance/`):
  - dashboard dedicata al coordinamento finanziario
  - gestione `preventivi` (`Quote`)
  - righe articolo su preventivi (`QuoteLine`): codice, descrizione, importo netto, importo lordo, quantita, sconto, codice IVA
  - gestione `fatture` (`Invoice`)
  - gestione `ordini lavoro` (`WorkOrder`)
  - snapshot KPI: pipeline preventivi, fatture aperte/pagate, alert scadenze
  - collegamento operativo rapido con `transactions` e `subscriptions`
- `subscriptions` (`/subs/`):
  - Subscription + SubscriptionOccurrence
  - status active/paused/canceled
  - interval day/week/month/year
  - legami con account, project, category, payee, tags
- `transactions` (`/transactions/`):
  - hub unificato movimenti (IN/OUT/XFER) con CRUD completo in modale
  - filtri live (tipo, range date, testo) via HTMX
  - orchestrazione UI via Stimulus (campi dinamici per tipo transazione)
  - layout e componenti UI basati su UIKit

### Progetti e operativita
- `projects` (`/projects/`):
  - CRUD project
  - CRUD category e customer
  - detail progetto con snapshot collegato (transactions/subscriptions/planner/routines)
  - storyboard progetto:
    - note con allegati
    - task rapidi
    - planner item rapidi
    - timeline azioni unificata
  - override hero actions per singolo progetto
- `todo` (`/todo/`):
  - Task con stato/priority/due date
  - associazione progetto esistente o creazione progetto inline
  - trasferimento rapido Task -> Planner
- `planner` (`/planner/`):
  - PlannerItem con amount/category/project/status
  - quando aggiungi item con project, crea automaticamente una `ProjectNote`
  - trasferimento rapido Planner -> Todo
- `routines` (`/routines/`):
  - Routine e RoutineItem settimanali
  - check settimanali (`RoutineCheck`) con stati planned/done/skipped
  - autoskip dei giorni passati nella settimana corrente
  - schema JSON per campi dinamici per item
  - dashboard mobile-first con componenti UIKit
  - interazioni `Fatto/Saltato/Riapri` via HTMX senza reload completo pagina
  - modal dati dinamici quando l'item ha campi schema, submit diretto quando non ci sono campi aggiuntivi
  - pannello rapido "Oggi" con contatori (totale, da fare, fatti, saltati)
  - filtri rapidi: tutte, solo oggi, solo da fare

### AI e knowledge
- `archibald` (`/archibald/`):
  - chat persistente per thread con storico giornaliero
  - conversation state OpenAI per thread (conversation/response id persistiti)
  - favorite toggle messaggi
  - insight cards per dominio (overview, tasks, expenses, subscriptions, planner, routines, projects)
  - arricchimento contesto automatico dai dati utente (`archibald/services.py`)
  - endpoint quick chat
- `ai_lab` (`/ai-lab/`):
  - tracking studio/esperimenti AI (area, status, prompt, result, next_step, resource_url)
- `link_storage` (`/link_storage/`):
  - CRUD semplice link categorizzati con importance + note

### Sicurezza
- `vault` (`/vault/`):
  - setup TOTP iniziale (one-time)
  - unlock/lock sessione con timeout
  - blocco temporaneo dopo tentativi falliti
  - item password/note con cifratura (`cryptography.Fernet`)

### Workspace tecnico
- `workbench` (`/workbench/`):
  - CRUD ticket tecnici (`WorkbenchItem`)
  - debug log cambiamenti (`DebugChangeLog` + middleware)
  - AI UI Generator (`/workbench/ai/ui-generator`)
  - AI App Generator (`/workbench/ai/app-generator`, solo superuser):
    - genera app Django base da prompt
    - fallback locale se OpenAI non configurata
  - DB schema explorer + Mermaid ERD (`/workbench/debug/schema`)

## Modello dati (alto livello)

- Base astratta:
  - `common.TimeStampedModel`
  - `common.OwnedModel` (record scoped per user)
- Hub finanza:
  - `transactions.Transaction` collega `Account`, `Currency`, `Project`, `Category`, `Payee`, `IncomeSource`, `Tag`, `Subscription`
  - `finance_hub.Quote`, `finance_hub.Invoice`, `finance_hub.WorkOrder` per ciclo commerciale/operativo
- Scheduler:
  - `subscriptions.Subscription` -> `SubscriptionOccurrence`
  - `routines.Routine` -> `RoutineItem` -> `RoutineCheck`
- Progetti:
  - `Project` con `Customer`, `Category`, `ProjectNote`

## Setup locale

```bash
cd mio_master
cp .env.local.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Apri: `http://127.0.0.1:8000/`

## Variabili ambiente

Il progetto carica automaticamente `.env` in root (`mio_master/.env`) se presente.

Template consigliati:

- Locale: `.env.local.example`
- VPS/Produzione: `.env.vps.example`

In pratica:

- locale -> copia `.env.local.example` in `.env`
- vps -> copia `.env.vps.example` in `.env`

Obbligatorie in produzione:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=false`
- `DJANGO_ALLOWED_HOSTS`
- `DATABASE_URL` (PostgreSQL)

Opzionali (feature specifiche):

- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (default: `gpt-4o-mini`)
- `OPENAI_MODEL_ARCHIBALD` (override modello solo per Archibald, default: `gpt-5.4`)
- `ARCHIBALD_REASONING_EFFORT` (es. `low|medium|high|xhigh`; default auto `high` su GPT-5)
- `ARCHIBALD_USE_CONVERSATIONS` (`true|false`, default: `true`)
- `VAULT_ENCRYPTION_KEY` (consigliata in prod)
- `VAULT_TOTP_ISSUER` (default: `MIO Vault`)
- `VAULT_SESSION_TIMEOUT_SECONDS` (default: `600`)

Note:

- Se `OPENAI_API_KEY` manca, le feature AI mostrano errore controllato o fallback.
- Se `VAULT_ENCRYPTION_KEY` manca, in locale viene derivata da `SECRET_KEY` (fallback deterministico).

## Deploy VPS (Docker)

Stack container:

- `web`: Django + Gunicorn
- `db`: PostgreSQL 16
- `caddy`: reverse proxy + static/media + HTTPS automatico

File principali:

- `Dockerfile`
- `docker-compose.yml`
- `docker/entrypoint.sh`
- `docker/caddy/Caddyfile`
- `.env.vps.example`
- `.env.local.example`
- `.env.docker.example` (legacy/compatibilita)

Setup rapido su VPS:

1. Copia progetto su VPS.
2. Crea `.env` partendo da `.env.vps.example`.
  - Per HTTPS reale imposta:
    - `CADDY_SITE_HOST=tuo-dominio.it`
    - `DJANGO_ALLOWED_HOSTS=tuo-dominio.it,www.tuo-dominio.it`
    - `DJANGO_CSRF_TRUSTED_ORIGINS=https://tuo-dominio.it,https://www.tuo-dominio.it`
3. Avvia stack:

```bash
docker compose up -d --build
```

Controlli:

```bash
docker compose ps
docker compose logs -f web
docker compose logs -f caddy
```

Update deploy:

```bash
git pull
docker compose up -d --build
```

Oppure con script rapido (no backup):

```bash
./deploy_vps.sh
```

Note:

- Il container `web` esegue automaticamente:
  - `python manage.py migrate --noinput`
  - `python manage.py collectstatic --noinput`
  - avvio `gunicorn`
- In `docker-compose.yml` `DATABASE_URL` e costruita automaticamente verso il servizio `db`.
- Caddy emette e rinnova certificati TLS automaticamente quando `CADDY_SITE_HOST` e un dominio pubblico risolvibile.

## Test

Sono presenti test Django in diversi moduli, tra cui:

- `ai_lab`
- `finance_hub`
- `planner`
- `projects`
- `todo`
- `vault`
- `workbench`

Esecuzione:

```bash
python manage.py test
```

Verifica recente (27 febbraio 2026):

- `python manage.py check` -> `OK`
- `python manage.py test routines.tests` -> `OK` (`2` test)

## Struttura repository (essenziale)

```text
mio_master/
  mio_master/        # settings, urls, wsgi, asgi
  common/            # modelli base astratti
  core/              # auth, dashboard, calendario, account
  subscriptions/     # abbonamenti, account, currency, tag
  finance_hub/       # dashboard finanza + preventivi/fatture/ordini lavoro
  income/ outcome/   # entrate/uscite su Transaction
  transactions/      # ledger unificato
  projects/          # progetti, clienti, categorie, storyboard
  todo/ planner/     # task e pianificazione
  routines/          # routine settimanali con check
  archibald/         # assistente AI contestuale
  ai_lab/            # tracking studi/esperimenti AI
  vault/             # vault cifrato + TOTP
  link_storage/      # archivio link rapido
  workbench/         # debug + generatori AI + schema explorer
  requirements.txt
  Dockerfile
  docker-compose.yml
  docker/
```
