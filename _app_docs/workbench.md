# workbench

## Scopo
L'app `workbench` e il toolbox tecnico per debug, generazione AI e manutenzione del monolite.

## Funzionalita principali
- CRUD ticket tecnici (`WorkbenchItem`).
- AI UI Generator.
- AI App Generator (con setup post-generation).
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
- `GET/POST /workbench/ai/ui-generator`
- `GET/POST /workbench/ai/app-generator`
- `GET /workbench/debug/logs`
- `GET /workbench/debug/api-endpoints`
- `GET /workbench/debug/schema`
- `GET /workbench/debug/radicale`

## Template/UI principali
- `workbench/dashboard.html`
- `workbench/ai_ui_generator.html`
- `workbench/ai_app_generator.html`
- `workbench/debug_logs.html`
- `workbench/api_endpoints.html`
- `workbench/db_schema.html`
- `workbench/radicale_debug.html`

## Integrazioni con altre app
- Analizza URL resolver globale di tutto il progetto.
- Usa introspezione DB e migration loader per audit tecnico.
- Interagisce con generatori (`app_builder.py`) e cleanup utility.

## Casi d'uso reali
- Prototipare nuove UI/app in modalita assistita.
- Ispezionare endpoint e schema dati durante debug.
- Ripulire in sicurezza artefatti di app generate.

## Note operative
- Alcune azioni sono limitate o sensibili (es. app generator/cleanup).
- Change log utile solo quando middleware debug e attivo.

## Copertura test esistente
- `AppBuilderTests`
- `WorkbenchCleanupViewTests`

## Debito tecnico / TODO
- Separare area generator da area debug in moduli distinti.
- Migliorare validazioni sicurezza sui prompt generator.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
