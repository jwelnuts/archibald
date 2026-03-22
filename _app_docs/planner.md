# planner

## Scopo
L'app `planner` gestisce promemoria/pianificazioni operative con possibile impatto economico.

## Funzionalita principali
- Dashboard planner con item pianificati e riepilogo stato.
- CRUD `PlannerItem`.
- Trasferimento item planner -> todo.
- Collegamento opzionale a progetto e categoria.
- Creazione automatica nota progetto quando aggiunto planner item con progetto.

## Modelli chiave
- `PlannerItem`: titolo, scadenza, importo, categoria, progetto, note, stato.

## View / Endpoint principali
- `GET /planner/`
- `GET/POST /planner/add`
- `GET/POST /planner/update?id=<id>`
- `GET/POST /planner/remove?id=<id>`
- `POST /planner/to-todo`

## Template/UI principali
- `planner/dashboard.html`
- `planner/add_item.html`
- `planner/update_item.html`
- `planner/remove_item.html`

## Integrazioni con altre app
- `todo`: trasferimento planner -> task.
- `projects`: link progetto/categoria e creazione `ProjectNote` di audit.

## Casi d'uso reali
- Gestire reminder operativi con data e contesto progetto.
- Spostare attività in execution operativa passando da planner a todo.

## Note operative
- Mapping stato planner->todo durante transfer.
- Form supporta quick create progetto/categoria.

## Copertura test esistente
- `PlannerDashboardTests`

## Debito tecnico / TODO
- Aggiungere vista timeline/kanban planner.
- Migliorare dedup quando si trasferisce verso todo.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
