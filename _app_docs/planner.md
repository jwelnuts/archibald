# planner

## Scopo
L'app `planner` gestisce una wishlist personale: spese future, idee e pianificazioni non operative.

## Funzionalita principali
- Dashboard planner con item pianificati e riepilogo stato.
- CRUD `PlannerItem`.
- Collegamento opzionale a progetto e categoria.
- Creazione automatica nota progetto quando aggiunto planner item con progetto.

## Modelli chiave
- `PlannerItem`: titolo, scadenza, importo, categoria, progetto, note, stato.

## View / Endpoint principali
- `GET /planner/`
- `GET/POST /planner/add`
- `GET/POST /planner/update?id=<id>`
- `GET/POST /planner/remove?id=<id>`

## Template/UI principali
- `planner/dashboard.html`
- `planner/add_item.html`
- `planner/update_item.html`
- `planner/remove_item.html`

## Integrazioni con altre app
- `projects`: link progetto/categoria e creazione `ProjectNote` di audit.

## Casi d'uso reali
- Pianificare spese personali/familiari con data obiettivo e importo.
- Tenere una wishlist ordinata con stato planned/done/skipped.

## Note operative
- Form supporta quick create progetto/categoria.

## Copertura test esistente
- `PlannerDashboardTests`

## Debito tecnico / TODO
- Aggiungere vista timeline/kanban planner.
- Aggiungere priorità nativa sulle voci wishlist.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
