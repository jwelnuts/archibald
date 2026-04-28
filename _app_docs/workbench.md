# workbench

## Scopo
L'app `workbench` e il toolbox tecnico per debug, generazione AI e manutenzione del monolite.

## Funzionalita principali
- CRUD ticket tecnici (`WorkbenchItem`).
- AI App Generator rimosso.
- Cleanup app generate/orfane.
- Debug logs con change tracking (`DebugChangeLog`).
- API endpoints explorer.
- DB schema explorer con output visuale.
- Pannello debug Radicale/CalDAV.

## Modelli chiave
- `WorkbenchItem`: item operativi tecnici (kind/status/note).
- `DebugChangeLog`: storico cambiamenti debug middleware.

## View / Endpoint principali
- `GET /workbench/`: dashboard.
- `POST /workbench/api/add|update|remove`
- `POST /workbench/api/cleanup-generated-app`
- `GET /workbench/debug/logs`
- `GET /workbench/debug/api-endpoints`
- `GET /workbench/debug/schema`
- `GET /workbench/debug/radicale`

## Template/UI principali
- `workbench/dashboard.html`
- `workbench/debug_logs.html`
- `workbench/api_endpoints.html`
- `workbench/db_schema.html`
- `workbench/radicale_debug.html`

## Integrazioni con altre app
- Analizza URL resolver globale di tutto il progetto.
- Usa introspezione DB per audit tecnico.

## Casi d'uso reali
- Ispezionare endpoint e schema dati durante debug.

## Note operative
- Change log utile solo quando middleware debug e attivo.

## Copertura test esistente
- `WorkbenchDashboardAuthTests`
- `WorkbenchDavControlPanelTests`

## Debito tecnico / TODO
- Nessuno.

## Ultimo aggiornamento doc
- Data: 2026-04-27
- Autore: Codex
