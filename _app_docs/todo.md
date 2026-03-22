# todo

## Scopo
L'app `todo` gestisce task operativi con stati, priorita e integrazione planner.

## Funzionalita principali
- Dashboard task con ordinamento per stato/scadenza.
- CRUD task.
- Cambio stato rapido (supporto HTMX/AJAX).
- Trasferimento task -> planner mantenendo contesto.
- KPI open/in_progress/done/overdue/today.

## Modelli chiave
- `Task`: titolo, tipo, stato, priorita, scadenza, progetto/categoria, note.

## View / Endpoint principali
- `GET /todo/`
- `GET/POST /todo/api/add`
- `GET/POST /todo/api/update?id=<id>`
- `GET/POST /todo/api/remove?id=<id>`
- `POST /todo/api/status`: cambio stato.
- `POST /todo/to-planner`: trasferimento a planner.

## Template/UI principali
- `todo/dashboard.html`
- `todo/add_task.html`
- `todo/update_task.html`
- `todo/remove_task.html`
- `todo/partials/task_status_oob.html`
- `todo/partials/task_row.html`

## Integrazioni con altre app
- `planner`: transfer task -> planner item.
- `projects`: link a progetto/categoria.

## Casi d'uso reali
- Gestire daily execution task con update stato immediato.
- Spostare attività strategiche da todo verso planner.

## Note operative
- Endpoint `set_status` supporta fallback full-page + modalità HTMX/AJAX.
- Transfer conserva parte metadati task nel campo note planner.

## Copertura test esistente
- `TodoProjectBindingTests`

## Debito tecnico / TODO
- Aggiungere batch update stato.
- Inserire reminder automatici su task overdue ad alta priorita.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
