# todos

## Scopo
L'app `todos` gestisce todo ricorrenti settimanali con item, check stato e statistiche.

## Funzionalita principali
- CRUD todo e todo item.
- Check giornalieri/settimanali con stato (`planned/done/skipped`).
- Supporto schema dati custom per item (campi strutturati nel check).
- Dashboard todo con filtri settimana/categoria.
- Pagina statistiche completamento.

## Modelli chiave
- `TodoCategory`: categoria todo.
- `Todo`: contenitore todo.
- `TodoItem`: attivita ricorrente con weekday, range orario, note, schema JSON.
- `TodoCheck`: stato esecuzione settimanale item + dati JSON.

## View / Endpoint principali
- `GET /todos/`: dashboard.
- `GET /todos/stats`: statistiche.
- `POST /todos/check`: aggiorna check item.
- Todo CRUD: `/todos/api/add|update|remove`
- Item CRUD: `/todos/items/add|update|remove`

## Template/UI principali
- `todos/dashboard.html`
- `todos/stats.html`
- `todos/add_todo.html`
- `todos/update_todo.html`
- `todos/add_item.html`
- `todos/update_item.html`
- `todos/partials/check_item_oob.html`

## Integrazioni con altre app
- `projects`: item todo opzionalmente legato a progetto.
- `core` API mobile usa servizi todos per endpoint app mobile.

## Casi d'uso reali
- Definire checklist settimanali personali/professionali.
- Tracciare completamento todo nel tempo con metriche.

## Note operative
- Servizi CRUD dedicati in `todos/services.py` con error code applicativi.
- Supporto tempo start/end normalizzato e weekday validato.

## Copertura test esistente
- `TodoCheckHTMXTests`
- `TodoItemCreationTests`
- `TodoCrudTests`
- `TodoStatsPageTests`

## Debito tecnico / TODO
- Migliorare UI builder schema campi custom todo item.
- Aggiungere export storico check.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
