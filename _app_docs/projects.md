# projects

## Scopo
L'app `projects` e il centro di orchestrazione dei progetti utente.
Gestisce anagrafica progetto, cliente, categoria, sotto-lavori (sub-project), attività operative e storyboard unificato.
Funziona anche da punto di collegamento trasversale con moduli economici e operativi (transazioni, planner, todo, routine, abbonamenti, preventivi).

## Funzionalita principali
- Dashboard portfolio con scope (`active`, `archived`, `all`) e KPI aggregati per progetto.
- CRUD progetto con scelta cliente da `contacts` e categoria esistente o creazione rapida categoria.
- Dettaglio progetto "cockpit" con quick actions, metriche e operazioni rapide su planner/subscriptions/subprojects/preventivi.
- Gestione sub-progetti con stato/priorita/progresso e relativo dettaglio attività.
- Storyboard progetto: inserimento rapido `note`, `task`, `planner` e log unificato filtrabile (con HTMX + Stimulus).
- Configurazione hero actions per singolo progetto (`projects_detail`, `projects_storyboard`).
- CRUD categorie progetto.
- Creazione preventivo da progetto (`/projects/quotes/add`) con progetto/cliente bloccati e import righe da listino contatto (`contacts.toolbox`).

## Modelli chiave
- `Customer`: cliente legacy del progetto (`name`, `email`, `phone`, `notes`), univoco per `owner+name`.
- `Project`: entita principale (`name`, `customer`, `category`, `description`, `is_archived`).
- `Category`: categoria condivisa (tabella `common_category`) riusata anche da altre app.
- `ProjectNote`: appunti progetto con allegato opzionale (usata anche nello storyboard).
- `SubProject`: sotto-progetto operativo con `status`, `priority`, date e `% completamento`.
- `SubProjectActivity`: attività del sotto-progetto (`status`, `ordering`, `due_date`).
- `ProjectHeroActionsConfig`: visibilita azioni hero per utente+progetto (config JSON).

## View / Endpoint principali
- `GET /projects/`: dashboard portfolio con metriche aggregate multi-app.
- `GET/POST /projects/api/add`: creazione progetto.
- `GET/POST /projects/api/update?id=<project_id>`: modifica progetto.
- `GET/POST /projects/api/remove?id=<project_id>`: rimozione progetto.
- `GET/POST /projects/view?id=<project_id>`: dettaglio progetto + azioni rapide inline (transazioni, abbonamenti, planner, preventivi, routine, sub-progetti).
- `GET/POST /projects/subprojects/add?project=<project_id>`: nuovo sub-progetto.
- `GET/POST /projects/subprojects/update?id=<subproject_id>`: modifica sub-progetto.
- `GET/POST /projects/subprojects/view?id=<subproject_id>`: dettaglio sub-progetto + CRUD attività.
- `GET/POST /projects/storyboard?id=<project_id>`: hub storyboard (note/task/planner).
- `GET /projects/storyboard/log?id=<project_id>`: partial HTMX del log filtrato.
- `GET/POST /projects/hero-actions?id=<project_id>`: configurazione azioni visibili.
- `GET /projects/categories/`: lista categorie.
- `GET/POST /projects/categories/add`: creazione categoria.
- `GET/POST /projects/categories/update?id=<category_id>`: modifica categoria.
- `GET/POST /projects/categories/remove?id=<category_id>`: rimozione categoria.
- `GET/POST /projects/quotes/add?project=<project_id>`: creazione preventivo da contesto progetto.

## Template/UI principali
- `projects/dashboard.html`: vista portfolio con tabella/stack responsive progetti.
- `projects/project_detail.html`: cockpit operativo per singolo progetto.
- `projects/storyboard.html` + `projects/partials/storyboard_log.html`: inserimento rapido e timeline filtrabile.
- `projects/subproject_form.html`: create/update sub-project.
- `projects/subproject_detail.html`: gestione attività sub-project.
- `projects/hero_actions.html`: personalizzazione azioni hero.
- `projects/add_project.html`, `projects/update_project.html`, `projects/remove_project.html`.
- `projects/categories.html`, `projects/add_category.html`, `projects/update_category.html`, `projects/remove_category.html`.
- Riuso template `finance_hub/quote_form.html` in modalità `project_quote_mode` per il preventivo da progetto.

## Integrazioni con altre app
- `contacts`:
  - `ProjectForm` usa i contatti attivi come sorgente cliente (`customer_choice`).
  - Sync cliente legacy via `upsert_contact` + `ensure_legacy_records_for_contact`.
  - `add_project_quote` legge i listini da `ContactToolbox -> ContactPriceList`.
- `finance_hub`:
  - Creazione quote da progetto con `QuoteForm` + `QuoteLineFormSet`.
  - Applicazione IVA riga e refresh totali quote.
- `transactions`, `subscriptions`, `todo`, `planner`, `routines`:
  - Dashboard e project detail aggregano KPI e consentono operazioni rapide.
- `core`:
  - Hero actions globali (`core.hero_actions`) e override per progetto (`ProjectHeroActionsConfig`).
- `static/core/projects_storyboard.js`:
  - Controller Stimulus per filtri log storyboard con submit HTMX debounce.

## Casi d'uso reali
- Monitorare lo stato operativo/economico di tutti i progetti da un'unica dashboard.
- Entrare nel dettaglio progetto e aggiornare rapidamente stato planner/subscription/subproject.
- Entrare nel dettaglio progetto e visualizzare gli ultimi preventivi collegati con accesso diretto in modifica.
- Creare e tracciare attività di un sub-progetto con ordinamento e stato.
- Usare storyboard come timeline mista: note ricche, task, reminder e transazioni.
- Configurare i pulsanti rapidi visibili in base al proprio flusso utente.
- Generare un preventivo direttamente da progetto importando righe dai listini del contatto cliente.

## Note operative
- Tutte le query sono scoped per `owner` (multi-utente per record ownership).
- `ProjectForm` sincronizza prima i contatti legacy (`sync_contacts_from_legacy`) e poi risolve `Customer` da `Contact`.
- `Category` e condivisa (`db_table = common_category`), non esclusiva di `projects`.
- `project_detail` gestisce varie azioni `POST` con `action` discriminator nello stesso endpoint.
- Storyboard log:
  - Filtri per tipo (`all`, `note`, `task`, `planner`, `transaction`), range date e ricerca testuale.
  - Rendering partial con HTMX per aggiornamento dinamico.
- `add_project_quote`:
  - Blocca progetto e cliente nel form quote.
  - Se cliente presente, tenta aggancio listini attivi del contatto corrispondente.

## Copertura test esistente
Classi principali in `projects/tests.py`:
- `ProjectStoryboardFormsTests`
- `ProjectStoryboardLogTests`
- `ProjectDashboardContextTests`
- `SubProjectFlowTests`
- `ProjectDetailPlannerModalTests`
- `ProjectQuoteBuilderTests`

## Debito tecnico / TODO
- Ridurre duplicazione logica quote tra `projects.views` e `finance_hub.views` (helpers condivisi in service comune).
- Valutare split di `projects/views.py` in moduli piu piccoli (dashboard, detail, subprojects, storyboard, categories, quotes).
- Standardizzare naming/status labels (`SubProject.Status` contiene label inglesi misti con UI italiana).
- Estendere test integrazione su import righe da listino lato UI (attualmente coverage principale lato view/POST).

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
