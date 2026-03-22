# agenda

## Scopo
L'app `agenda` fornisce la vista calendario operativa mensile.
Unifica agenda classica, task, planner, routine e worklog giornaliero in un unico pannello.

## Funzionalita principali
- Vista mensile con giorno selezionato e pannelli dinamici.
- Gestione `AgendaItem` (attivita/reminder) e stato done/planned.
- Inserimento rapido task (`todo`) e planner item (`planner`) dal contesto agenda.
- Gestione `WorkLog` giornaliero con ore e pausa pranzo.
- Preferenze UI agenda salvate per utente (densita, accent, sezioni).

## Modelli chiave
- `AgendaItem`: voce agenda con tipo, data/ora, progetto, stato e note.
- `WorkLog`: log giornaliero ore lavorate (vincolo un record per giorno per owner).

## View / Endpoint principali
- `GET /agenda/`: dashboard calendario completa.
- `GET /agenda/panel`: pannello eventi giorno (partial).
- `GET /agenda/snapshot`: snapshot KPI agenda (partial).
- `POST /agenda/item-action`: azioni rapide su item agenda.
- `GET/POST /agenda/preferences`: salva/aggiorna preferenze vista.

## Template/UI principali
- `agenda/dashboard.html`
- `agenda/partials/panel.html`
- `agenda/partials/snapshot.html`

## Integrazioni con altre app
- `todo`: usa `Task` e `TaskForm` nel calendario.
- `planner`: usa `PlannerItem` e `PlannerItemForm`.
- `routines`: mostra check e stato routine settimanali.
- `projects`: usa `ProjectNote` per contesto attività.
- `core`: preferenze salvate in `UserNavConfig`.

## Casi d'uso reali
- Pianificare il mese e vedere in anticipo collisioni tra task/planner/routine.
- Registrare ore lavorate giornaliere dal calendario.
- Usare agenda come cockpit unico operativo giornaliero.

## Note operative
- `WorkLog` ha unique constraint su `(owner, work_date)`.
- Preferenze agenda sono normalizzate con whitelist valori consentiti.
- Endpoint partial usati per aggiornamenti dinamici UI.

## Copertura test esistente
- `AgendaDashboardTests`
- `AgendaLiveEndpointsTests`

## Debito tecnico / TODO
- Uniformare naming stato tra moduli (alcuni in italiano, alcuni in inglese).
- Aggiungere test di regressione su preferenze custom avanzate.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
