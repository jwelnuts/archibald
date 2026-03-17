# CalDAV Unification Plan (Agenda + Todo + Planner)

## Goal
Unificare i moduli `agenda`, `todo` e `planner` in un solo dominio operativo, con **CalDAV come source of truth**.

Obiettivo pratico:
- un solo backend dati per web, Thunderbird, Archidroid;
- una sola semantica di item operativi (`event` + `task`);
- ridurre duplicazioni e trasferimenti manuali (es. Todo -> Planner).

## Scope
In scope:
- `AgendaItem`, `Task`, `PlannerItem` e relativi flussi CRUD.
- Mapping verso `VEVENT` e `VTODO`.
- Introduzione modello unificato applicativo (`WorkItem`) come view/proiezione.

Out of scope (fase successiva):
- ACL team multi-tenant avanzate per singolo cliente/team.
- Rule engine Archibald (escalation SLA, policy custom per team).

## Target Architecture
1. **Radicale/CalDAV**: storage canonico di eventi e task.
2. **MIO domain service** (`workitems`): logica business unificata.
3. **UI unificata**: una vista “Operations/Agenda” con filtri (task, eventi, planner-like).
4. **Projection cache locale**: letture veloci + aggregazioni dashboard.

## Unified Domain Contract (`WorkItem`)
`WorkItem` è il contratto interno unico usato da UI/API, indipendente dal formato iCalendar.

Campi consigliati:
- `id` (uuid interno applicazione)
- `owner_id`
- `kind` (`event` | `task` | `worklog`)
- `title`
- `description`
- `start_at` (datetime nullable)
- `due_at` (datetime/date nullable)
- `all_day` (bool)
- `status`
- `priority`
- `project_id` (nullable)
- `category_id` (nullable)
- `amount` (decimal nullable)
- `source_module` (`agenda|todo|planner|system`)
- `dav_collection`
- `dav_href`
- `dav_uid`
- `dav_etag`
- `dav_type` (`VEVENT|VTODO`)
- `synced_at`
- `is_deleted` (soft delete locale)

## Canonical CalDAV Mapping
### `Task` -> `VTODO` / `VEVENT`
Regola:
- `item_type=APPOINTMENT` -> `VEVENT`
- `item_type=TASK|REMINDER` -> `VTODO`

Mapping:
- `title` -> `SUMMARY`
- `note` -> `DESCRIPTION`
- `due_date/due_time` -> `DUE` (`VTODO`) o `DTSTART` (`VEVENT`)
- `priority`:
  - `HIGH` -> `PRIORITY:1`
  - `MEDIUM` -> `PRIORITY:5`
  - `LOW` -> `PRIORITY:9`
- `status`:
  - `OPEN` -> `NEEDS-ACTION`
  - `IN_PROGRESS` -> `IN-PROCESS`
  - `DONE` -> `COMPLETED`
- `project/category` -> `CATEGORIES` + `X-MIO-PROJECT-ID`, `X-MIO-CATEGORY-ID`

### `PlannerItem` -> `VTODO`
Mapping:
- `title` -> `SUMMARY`
- `note` -> `DESCRIPTION`
- `due_date` -> `DUE` (all-day se senza ora)
- `status`:
  - `PLANNED` -> `NEEDS-ACTION`
  - `DONE` -> `COMPLETED`
  - `SKIPPED` -> `CANCELLED`
- `amount` -> `X-MIO-AMOUNT`
- `project/category` -> `CATEGORIES` + `X-MIO-*`

### `AgendaItem` -> `VEVENT` / `VTODO`
Regola:
- `item_type=ACTIVITY` -> `VEVENT`
- `item_type=REMINDER` -> `VTODO`

Mapping:
- `title` -> `SUMMARY`
- `note` -> `DESCRIPTION`
- `due_date/due_time` -> `DTSTART` (`VEVENT`) o `DUE` (`VTODO`)
- `status`:
  - per `VTODO`: `PLANNED -> NEEDS-ACTION`, `DONE -> COMPLETED`
  - per `VEVENT`: `STATUS:CONFIRMED` + `X-MIO-DONE:true|false`
- `project` -> `X-MIO-PROJECT-ID`

### `WorkLog` (opzionale fase 2)
`WorkLog` può diventare `VEVENT` con:
- `SUMMARY: Worklog`
- `DTSTART/DTEND`
- `X-MIO-TYPE:WORKLOG`
- `X-MIO-HOURS`, `X-MIO-LUNCH-BREAK-MINUTES`

## Collection Strategy
Per utente:
- `/{dav_user}/events/` (`VEVENT`)
- `/{dav_user}/tasks/` (`VTODO`)
- `/{dav_user}/worklog/` (opzionale)

Per team/progetto condiviso:
- `/team/<project-key>/events/`
- `/team/<project-key>/tasks/`

Nota:
- mantenere `events` e `tasks` separati semplifica client compatibility e filtri.

## Sync Model
Pattern consigliato:
1. Read collections (ctag o scan periodico).
2. Per ogni resource: salva `uid/href/etag`.
3. Aggiorna proiezione `WorkItem`.
4. In scrittura usa `If-Match` su `etag` per evitare overwrite ciechi.

Conflict policy iniziale:
- update concorrente con etag mismatch -> `409 conflict`;
- UI richiede reload e merge guidato.

## Migration Plan (No Downtime)
### Fase 0 - Preparation
- aggiungi `DavAccount` (già presente) e provisioning credenziali.
- aggiungi modulo `workitems` (service + projection model).
- non cambiare ancora le UI esistenti.

Exit criteria:
- utenti DAV creati automaticamente;
- file utenti Radicale sincronizzato.

### Fase 1 - Backfill + Mirror Write
- esporta dati storici da `Task/PlannerItem/AgendaItem` verso CalDAV.
- su nuove create/update/delete in moduli legacy, fai anche write su CalDAV.
- salva binding (`local_id <-> dav_uid/href/etag`).

Exit criteria:
- nuovi dati presenti sia in DB legacy che su CalDAV;
- audit mismatch vicino a zero.

### Fase 2 - CalDAV First Write
- tutte le scritture passano dal service `workitems` e vanno prima su CalDAV.
- tabelle legacy aggiornate solo come proiezione/compatibilità.
- endpoint UI legacy ancora disponibili ma instradati sul service unico.

Exit criteria:
- nessuna write diretta ai model legacy fuori dal service unificato.

### Fase 3 - UI/Model Consolidation
- nuova UI unica “Operations” sostituisce dashboard separate Agenda/Todo/Planner.
- depreca trasferimenti (`todo -> planner`, `planner -> todo`), non più necessari.
- legacy tables in read-only, poi rimozione graduale.

Exit criteria:
- un solo dominio `WorkItem` in uso;
- CalDAV unico backend operativo.

## Recommended Implementation Order
1. Creare app `workitems` con service e projection model.
2. Implementare mapping serializer `WorkItem <-> iCalendar`.
3. Implementare backfill command:
   - `python manage.py caldav_backfill --user <id|username>`
4. Implementare sync command:
   - `python manage.py caldav_sync --user <id|username> --direction both`
5. Rifattorizzare `todo/views.py`, `planner/views.py`, `agenda/views.py` per usare `workitems.service`.

## Risks
- timezone/all-day ambiguity (`DATE` vs `DATE-TIME`).
- status mapping `VEVENT` “done” non nativo.
- conflitti etag se più client scrivono in parallelo.
- ACL team: con regole troppo larghe rischi accesso cross-team.

## Decision Log (Initial)
- CalDAV è il backend canonico.
- `VTODO` per task/planner/reminder; `VEVENT` per appuntamenti/attività.
- metadati business in `X-MIO-*` per non perdere semantica dominio.
