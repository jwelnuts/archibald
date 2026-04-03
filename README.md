# MIO Master (archibald)

Snapshot documentazione: 27 febbraio 2026

Monolite Django per organizzazione personale: finanza, progetti, planner/todo/routine, knowledge link, vault cifrato e assistente AI (Archibald), con workspace tecnico (Workbench) per debug e generazione guidata.

## Stato attuale (snapshot)

- Backend: Django `6.0.1` con app multi-modulo e ownership per utente (`OwnedModel`).
- DB: PostgreSQL via `DATABASE_URL` (locale Docker + VPS).
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
- Bundle JS locale con `pnpm + Vite` (output in `core/static/core/dist`)
- HTMX da package npm (`htmx.org`) bootstrap globale in `core/static/core/app.js`
- Stimulus da package npm (`@hotwired/stimulus`) bootstrap in `core/static/core/stimulus.js`
- UIKit baseline bridge (`core/static/core/uikit_bridge.js`)
- Global style system LESS/CSS (`core/static/core/styles.less` -> `core/static/core/styles.css`)

### Sistema stili globale (LESS ibrido)

- Entrypoint unico: `core/static/core/styles.less`
  - importa foundation condivisa + moduli (`dashboard`, `profile`, `agenda`, `projects`, `routines`, `subscriptions`)
- Modalita sviluppo: `UI_STYLE_MODE=DEV`
  - middleware compila `styles.less` ad ogni richiesta HTML GET
  - i template caricano `core/styles.css` con cache-busting
- Modalita produzione/deploy: `UI_STYLE_MODE=PROD`
  - i template caricano solo `core/styles.css` compilato/minificato
- Workbench e volutamente escluso dal tema globale:
  - route `/workbench/*` senza `core/styles.less` / `core/styles.css`
  - stile dedicato: `workbench/static/workbench/irc-debug.css`

Note Stimulus:

- l'app Stimulus viene avviata globalmente da `core/static/core/app.js`
- i controller vengono registrati tramite helper in `core/static/core/stimulus.js`
- il modulo `routines` e gia migrato a controller Stimulus (`data-controller="routines"`)
- nessuna dipendenza runtime a CDN (`unpkg` rimosso)

### Toolchain JS (pnpm + Vite)

- installazione dipendenze:
  - `pnpm install --frozen-lockfile`
- build una tantum:
  - `pnpm build`
- watch build in sviluppo:
  - `pnpm dev`
- check JS nel flusso qualita:
  - `pnpm check:js`

Entrypoint bundle principali:

- `core/dist/app.js`
- `core/dist/dashboard.js`
- `core/dist/transactions.js`
- `core/dist/todo.js`
- `core/dist/routines.js`
- `core/dist/projects_storyboard.js`
- `core/dist/archibald.js`
- `core/dist/agenda.js`
- `core/dist/subscriptions_dashboard.js`

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
- `archibald_mail` (`/archibald-mail/`):
  - pannello controllo email per inbox dedicata (es. `archibald@miorganizzo.ovh`)
  - configurazione/login IMAP/SMTP gestiti da `.env` (nel pannello sono sola lettura)
  - CRUD flag inbound da pannello (`/archibald-mail/flags/`) per categorizzare email in ingresso
  - tabella categorie inbound con scelta da select e opzione `+nuova categoria` in triage inbox
  - inbox triage manuale (`/archibald-mail/inbox/`) per classificare email esterne senza flag
  - riepilogo email ogni 24h (destinatario configurabile da pannello in `notification_recipient`)
  - risposta email AI su richiesta esplicita via flag `[ARCHI]`
  - routing azioni da oggetto email (es. `[MEMORY]`, `#MEMORY`, `ACTION:MEMORY`)
  - notifiche email automatiche su task/planner/subscriptions/routines
  - log completo email inbound/outbound/notification/test
  - comandi management per automazione cron:
    - `python manage.py process_archibald_inbox`
    - `python manage.py send_archibald_notifications`
- `memory_stock` (`/memory-stock/`):
  - archivio personale di contenuti interessanti (titolo, URL, nota)
  - cattura automatica via email quando l'oggetto contiene flag memoria
  - gestione manuale da pannello (aggiungi/modifica/archivia/elimina)
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
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
```

Apri: `http://127.0.0.1/`

Se avvii Django fuori Docker, ricordati di compilare i bundle JS locali:

```bash
cd mio_master
pnpm install --frozen-lockfile
pnpm build
```

## Variabili ambiente

Il progetto carica automaticamente `.env` in root (`mio_master/.env`) se presente.

Template consigliati:

- Locale: `.env.local.example`
- VPS/Produzione: `.env.vps.example`

In pratica:

- locale -> copia `.env.local.example` in `.env`
- vps -> copia `.env.vps.example` in `.env`

Obbligatorie (locale Docker e produzione):

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=false`
- `UI_STYLE_MODE` (`DEV` compila LESS ad ogni richiesta HTML, `PROD` usa CSS compilato/minificato)
- `DJANGO_ALLOWED_HOSTS`
- `DATABASE_URL` (PostgreSQL)

Opzionali (feature specifiche):

- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `MOBILE_API_ALLOWED_ORIGINS` (origini consentite CORS per `/api/mobile/*`, es. `http://localhost,capacitor://localhost`)
- `MOBILE_API_ACCESS_TTL_SECONDS` (durata access token mobile, default `900`)
- `MOBILE_API_REFRESH_TTL_DAYS` (durata refresh token mobile, default `14`)
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (default: `gpt-4o-mini`)
- `OPENAI_MODEL_ARCHIBALD` (override modello solo per Archibald, default: `gpt-5-mini`)
- `ARCHIBALD_REASONING_EFFORT` (es. `low|medium|high|xhigh`; default auto `high` su GPT-5)
- `ARCHIBALD_USE_CONVERSATIONS` (`true|false`, default: `true`)
- `ARCHIBALD_MAIL_DEFAULT_INBOX` (default inbox precompilata nel pannello, es. `archibald@miorganizzo.ovh`)
- `ARCHIBALD_MAIL_IMAP_HOST` / `IMAP_HOST` (host IMAP fallback)
- `ARCHIBALD_MAIL_IMAP_PORT` / `IMAP_PORT` (porta IMAP fallback)
- `ARCHIBALD_MAIL_IMAP_USERNAME` / `IMAP_USERNAME` (username IMAP fallback)
- `ARCHIBALD_MAIL_IMAP_PASSWORD` (fallback password IMAP se non salvata nel DB)
- `ARCHIBALD_MAIL_SMTP_HOST` / `SMTP_HOST` (host SMTP fallback)
- `ARCHIBALD_MAIL_SMTP_PORT` / `SMTP_PORT` (porta SMTP fallback)
- `ARCHIBALD_MAIL_SMTP_USERNAME` / `SMTP_USERNAME` (username SMTP fallback)
- `ARCHIBALD_MAIL_SMTP_FROM` / `SMTP_FROM` (mittente SMTP fallback)
- `ARCHIBALD_MAIL_SMTP_PASSWORD` (fallback password SMTP se non salvata nel DB)
- `ARCHIBALD_MAIL_ALLOWED_SENDERS` (whitelist mittenti autorizzati, separati da virgola; se valorizzata ha priorita su `allowed_sender_regex`)
- `ARCHIBALD_MAIL_POLL_SECONDS` (ciclo standard worker, default `300`)
- `ARCHIBALD_MAIL_POLL_LIMIT` (limite email per ciclo standard, default `10`)
- `ARCHIBALD_MAIL_ARCHI_FAST_ENABLED` (abilita corsia veloce subject `ARCHI`, default `true`)
- `ARCHIBALD_MAIL_ARCHI_FAST_POLL_SECONDS` (intervallo corsia veloce ARCHI, default `5`)
- `ARCHIBALD_MAIL_ARCHI_FAST_LIMIT` (limite email per ciclo veloce ARCHI, default `3`)
- `CALDAV_ENABLED` (abilita integrazione CalDAV lato app, default `false`)
- `CALDAV_BASE_URL` (base URL server CalDAV, es. `http://tuo-dominio.it:5232/`)
- `CALDAV_SERVICE_USERNAME` (utente tecnico per sync via Archibald)
- `CALDAV_SERVICE_PASSWORD` (password utente tecnico per sync via Archibald)
- `CALDAV_LOGIN_DOMAIN` (dominio applicato agli username DAV utente, default `miorganizzo.ovh`)
- `CALDAV_DEFAULT_TEAM_COLLECTION` (collection team default, es. `team/progetto-generale`)
- `RADICALE_PUBLISHED_PORT` (porta host esposta per Radicale, default `5232`)
- `RADICALE_USERS_FILE` (path file utenti htpasswd condiviso con Radicale)
- `RADICALE_USERS_LOCK_FILE` (path lock file per scrittura atomica utenti DAV)
- `RADICALE_RIGHTS_FILE` (path file permessi Radicale condiviso con app)
- `VAULT_ENCRYPTION_KEY` (consigliata in prod)
- `VAULT_TOTP_ISSUER` (default: `MIO Vault`)
- `VAULT_SESSION_TIMEOUT_SECONDS` (default: `600`)

Note:

- Se `OPENAI_API_KEY` manca, le feature AI mostrano errore controllato o fallback.
- Se `VAULT_ENCRYPTION_KEY` manca, in locale viene derivata da `SECRET_KEY` (fallback deterministico).
- `LESS_DEV_MODE` resta supportata solo come fallback legacy (consigliato usare `UI_STYLE_MODE`).

## API Mobile (ArchiDroid)

Endpoint JSON dedicati alla app mobile:

- `POST /api/mobile/auth/login`
  - body: `{"identity":"email_o_username","password":"..."}` (+ opzionale `device_label`)
  - risposta: `access_token`, `refresh_token`, scadenze, dati utente
- `POST /api/mobile/auth/refresh`
  - body: `{"refresh_token":"..."}`
  - risposta: nuova coppia token (rotazione refresh inclusa)
- `POST /api/mobile/auth/logout`
  - header: `Authorization: Bearer <access_token>` (oppure body con `refresh_token`)
- `GET /api/mobile/dashboard`
  - header: `Authorization: Bearer <access_token>`
  - risposta: metriche dashboard + eventi recenti utente

Sicurezza:

- token salvati nel DB in forma hash (`sha256`)
- revoca sessione supportata
- access token a breve durata + refresh token ruotato

## Automazione email Archibald

Comandi principali:

```bash
python manage.py process_archibald_inbox
python manage.py send_archibald_notifications
python manage.py run_archibald_mail_worker --interval-seconds 300
```

`send_archibald_notifications` gestisce anche i prompt worklog automatici:

- ore `12:30` -> email check mattina `[WORKLOG_AM]`
- ore `18:30` -> email check pomeriggio `[WORKLOG_PM]`

Flag azione email disponibili:

- `memory_stock.save` tramite oggetto con uno dei pattern:
  - `[MEMORY]`
  - `#MEMORY`
  - `ACTION:MEMORY` (accetta anche `ACTION:MEMORY_STOCK.SAVE`)
- `todo.capture` tramite oggetto con:
  - `[TODO]`
  - `#TODO`
  - `ACTION:TODO`
  - stato attuale: salvataggio temporaneo in `Memory Stock`
- `transaction.capture` tramite oggetto con:
  - `[TRANSACTION]`
  - `#TRANSACTION`
  - `#TX`
  - `ACTION:TRANSACTION`
  - stato attuale: salvataggio temporaneo in `Memory Stock`
- `reminder.capture` tramite oggetto con:
  - `[REMINDER]`
  - `#REMINDER`
  - `ACTION:REMINDER`
  - stato attuale: salvataggio temporaneo in `Memory Stock`
- `archi.reply` tramite oggetto con:
  - `[ARCHI]`
  - `#ARCHI`
  - `ACTION:ARCHI`
  - risposta AI immediata (corsia veloce worker)
- `worklog.capture_am` tramite oggetto con:
  - `[WORKLOG_AM]`
  - `#WORKLOG_AM`
  - `ACTION:WORKLOG_AM`
  - rispondi con fascia oraria mattina (es. `09:00-12:30`) per aggiornare `agenda.WorkLog`
- `worklog.capture_pm` tramite oggetto con:
  - `[WORKLOG_PM]`
  - `#WORKLOG_PM`
  - `ACTION:WORKLOG_PM`
  - rispondi con ore pomeriggio (es. `4 ore`) o fascia oraria (es. `14:00-18:30`)
  - il backend calcola automaticamente la pausa pranzo e aggiorna `agenda.WorkLog`

Esempio `cron` (ogni 5 minuti inbox, notifiche giornaliere con controllo orario interno):

```bash
*/5 * * * * cd /path/mio_master && /path/mio_master/.venv/bin/python manage.py process_archibald_inbox >> /var/log/mio_archibald_mail.log 2>&1
*/15 * * * * cd /path/mio_master && /path/mio_master/.venv/bin/python manage.py send_archibald_notifications >> /var/log/mio_archibald_notify.log 2>&1
```

In alternativa al cron, puoi usare il worker continuo:

```bash
python manage.py run_archibald_mail_worker --interval-seconds 300
```

Opzioni utili:

- `--run-once` esegue un solo ciclo (debug).
- `--user <username|email>` limita il polling a un utente.
- `--force` ignora `is_enabled`.
- `--archi-fast-seconds` imposta la cadenza della corsia veloce `[ARCHI]`.
- `--archi-fast-limit` imposta il limite email per ciclo veloce `[ARCHI]`.
- `--disable-archi-fast` disabilita la corsia veloce `[ARCHI]`.

## Deploy VPS (Docker)

Stack container:

- `web`: Django + Gunicorn
- `mail_worker`: polling inbox Archibald a intervallo costante (default 300s)
- `db`: PostgreSQL 16
- `radicale`: server CalDAV/CardDAV (calendari e contatti)
- `caddy`: reverse proxy + static/media + HTTPS automatico

File principali:

- `Dockerfile`
- `docker-compose.yml`
- `push_full.fish` (push locale completo, con esclusione `.env`)
- `docker/entrypoint.sh`
- `docker/caddy/Caddyfile`
- `docker/radicale/config`
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
  - `.env` resta privato: non viene tracciato da git e non entra nel build context Docker.
3. Avvia stack:

```bash
docker compose up -d --build
```

Controlli:

```bash
docker compose ps
docker compose logs -f web
docker compose logs -f mail_worker
docker compose logs -f radicale
docker compose logs -f caddy
```

Update deploy (locale -> VPS):

```bash
./push_full.fish -m "chore: update progetto"
```

Push + deploy remoto in un unico comando (opzionale):

```bash
./push_full.fish \
  -m "chore: update progetto" \
  --deploy-vps \
  --vps-host ubuntu@vps-b054ede5 \
  --vps-path ~/archibald
```

Deploy diretto sulla VPS:

```bash
./deploy_vps.sh --branch main --force-sync
```

Note:

- Il container `web` esegue automaticamente:
  - `python manage.py migrate --noinput`
  - `python manage.py sync_radicale_users`
  - `python manage.py compile_less --quiet` (`DEV`) oppure `--quiet --minify` (`PROD`)
  - `python manage.py collectstatic --noinput`
  - avvio `gunicorn`
- In `docker-compose.yml` `DATABASE_URL` e costruita automaticamente verso il servizio `db`.
- Caddy emette e rinnova certificati TLS automaticamente quando `CADDY_SITE_HOST` e un dominio pubblico risolvibile.
- Radicale viene esposto direttamente sulla porta host `5232` (configurabile con `RADICALE_PUBLISHED_PORT`).
- `deploy_vps.sh` preserva sempre `.env` locale (backup/ripristino) e in `--force-sync` pulisce gli untracked mantenendo `.env`.
- Opzioni utili `deploy_vps.sh`: `--autostash`, `--force-sync`, `--branch <nome>`, `--skip-checks`.
- `mail_worker` usa:
  - `ARCHIBALD_MAIL_POLL_SECONDS` (default `300`)
  - `ARCHIBALD_MAIL_POLL_LIMIT` (default `10`)
  - `ARCHIBALD_MAIL_ARCHI_FAST_ENABLED` (default `true`)
  - `ARCHIBALD_MAIL_ARCHI_FAST_POLL_SECONDS` (default `5`)
  - `ARCHIBALD_MAIL_ARCHI_FAST_LIMIT` (default `3`)

## CalDAV Team (Radicale)

Convenzioni operative base:

- endpoint CalDAV/CardDAV: `http://<host>:5232/` (oppure URL reverse proxy personalizzato)
- utenti DAV applicativi: provisioning automatico alla registrazione utente (stessa password dell'account Django)
- calendario condiviso team: collection sotto `team/<nome-progetto>`
- utenti esterni DAV: gestibili da profilo utente con permessi per calendario (sync su file `RADICALE_RIGHTS_FILE`)

Esempio URL collection condivisa:

- `http://<host>:5232/team/progetto-generale/`

Nota client CalDAV:

- diversi client scoprono automaticamente solo le collection sotto `/USERNAME/`;
- le collection condivise sotto `/team/...` vanno quindi aggiunte con URL esplicito.

Provisioning utente:

- su signup (`/accounts/signup/`) viene creato `core.DavAccount` con username DAV dedicato
- la password DAV viene allineata alla stessa password dell'account Django
- su cambio password (`/accounts/password_change/`) viene sincronizzata anche la credenziale DAV
- gestione DAV avanzata da UI: `/profile/dav/` (calendari, utenti esterni, grant)

Sync manuale file utenti Radicale (se necessario):

```bash
python manage.py sync_radicale_users
```

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
  archibald_mail/    # inbox email Archibald + notifiche
  memory_stock/      # archivio memorie salvate anche da email
  ai_lab/            # tracking studi/esperimenti AI
  vault/             # vault cifrato + TOTP
  link_storage/      # archivio link rapido
  workbench/         # debug + generatori AI + schema explorer
  requirements.txt
  Dockerfile
  docker-compose.yml
  docker/
    radicale/
```
