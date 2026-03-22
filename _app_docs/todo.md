# todo

## Scopo
L'app `todo` gestisce task operativi con stati, priorita e sync `VTODO` su DAV.

## Funzionalita principali
- Dashboard task con ordinamento per stato/scadenza.
- CRUD task.
- Cambio stato rapido (supporto HTMX/AJAX).
- Sync automatica `Task -> VTODO` su create/update/status/delete.
- Sync manuale completa delle task verso DAV.
- KPI open/in_progress/done/overdue/today.

## Modelli chiave
- `Task`: titolo, tipo, stato, priorita, scadenza, progetto/categoria, note.

## View / Endpoint principali
- `GET /todo/`
- `GET/POST /todo/api/add`
- `GET/POST /todo/api/update?id=<id>`
- `GET/POST /todo/api/remove?id=<id>`
- `POST /todo/api/status`: cambio stato.
- `POST /todo/api/sync-vtodo`: sync completa verso DAV.

## Template/UI principali
- `todo/dashboard.html`
- `todo/add_task.html`
- `todo/update_task.html`
- `todo/remove_task.html`
- `todo/partials/task_status_oob.html`
- `todo/partials/task_row.html`

## Integrazioni con altre app
- `projects`: link a progetto/categoria.
- `core/dav`: provisioning account e collection CalDAV.

## Casi d'uso reali
- Gestire daily execution task con update stato immediato.
- Allineare task interne con client DAV tramite `VTODO`.

## Note operative
- Endpoint `set_status` supporta fallback full-page + modalità HTMX/AJAX.
- Collection personale di default usata per sync: `CALDAV_DEFAULT_USER_COLLECTION` (default `personal_dav`).

## Copertura test esistente
- `TodoProjectBindingTests`

## Debito tecnico / TODO
- Aggiungere batch update stato.
- Inserire reminder automatici su task overdue ad alta priorita.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
