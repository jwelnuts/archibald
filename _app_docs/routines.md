# routines

## Scopo
L'app `routines` gestisce routine ricorrenti settimanali con item, check stato e statistiche.

## Funzionalita principali
- CRUD routine e routine item.
- Check giornalieri/settimanali con stato (`planned/done/skipped`).
- Supporto schema dati custom per item (campi strutturati nel check).
- Dashboard routine con filtri settimana/categoria.
- Pagina statistiche completamento.

## Modelli chiave
- `RoutineCategory`: categoria routine.
- `Routine`: contenitore routine.
- `RoutineItem`: attivita ricorrente con weekday, range orario, note, schema JSON.
- `RoutineCheck`: stato esecuzione settimanale item + dati JSON.

## View / Endpoint principali
- `GET /routines/`: dashboard.
- `GET /routines/stats`: statistiche.
- `POST /routines/check`: aggiorna check item.
- Routine CRUD: `/routines/api/add|update|remove`
- Item CRUD: `/routines/items/add|update|remove`

## Template/UI principali
- `routines/dashboard.html`
- `routines/stats.html`
- `routines/add_routine.html`
- `routines/update_routine.html`
- `routines/add_item.html`
- `routines/update_item.html`
- `routines/partials/check_item_oob.html`

## Integrazioni con altre app
- `projects`: item routine opzionalmente legato a progetto.
- `core` API mobile usa servizi routines per endpoint app mobile.

## Casi d'uso reali
- Definire checklist settimanali personali/professionali.
- Tracciare completamento routine nel tempo con metriche.

## Note operative
- Servizi CRUD dedicati in `routines/services.py` con error code applicativi.
- Supporto tempo start/end normalizzato e weekday validato.

## Copertura test esistente
- `RoutineCheckHTMXTests`
- `RoutineItemCreationTests`
- `RoutineCrudTests`
- `RoutineStatsPageTests`

## Debito tecnico / TODO
- Migliorare UI builder schema campi custom routine item.
- Aggiungere export storico check.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
