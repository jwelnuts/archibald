---
name: implementation-strategy
description: MIO project implementation strategy, architecture patterns, and development workflow for Django + HTMX + Stimulus + UIKit
---

# Implementation Strategy — MIO Project

Guida alla strategia implementativa per il monolite MIO. Fornisce pattern architetturali, ordine di implementazione, convenzioni e checklist per ogni feature.

---

## Architettura (6 Layer)

```
L0 common → L1 core → L2 hubs → L3 ops → L4 archibald_mail
                                      → isolati: vault, memory_stock, link_storage, workbench
```

**Regola inviolabile:** mai import da un layer superiore verso uno inferiore. Un'app L3 può importare da L2, L1, L0 ma MAI da L4.

### Cosa mettere dove

| Layer | App | Responsabilità |
|-------|-----|---------------|
| L0 | `common` | `OwnedModel`, `TimeStampedModel`, upload paths |
| L1 | `core` | Auth, dashboard globale, API mobile, DAV, hero actions globali |
| L2 | `finance_hub`, `projects`, `contacts`, `subscriptions` | Orchestrazione dominio, modelli condivisi |
| L3 | `transactions`, `todo`, `planner`, `routines`, `agenda`, `income`, `outcome` | Operatività, usa modelli L2 |
| L4 | `archibald`, `archibald_mail` | AI, email, dipende da tutti i layer inferiori |
| Iso | `vault`, `memory_stock`, `link_storage`, `workbench`, `ai_lab` | Indipendenti o dipendenze solo L0 |

---

## Flusso di Implementazione

Per ogni feature, seguire questo ordine:

### 1. Analisi
- Identificare il layer corretto per la feature
- Elencare i modelli esistenti da toccare (o nuovi da creare)
- Identificare le dipendenze cross-app
- Decidere il pattern UI: full page, HTMX partial, Stimulus widget

### 2. Modelli (`models.py`)
```python
from common.models import OwnedModel, TimeStampedModel

class MyModel(OwnedModel, TimeStampedModel):
    name = models.CharField(max_length=120)
    # ...
    class Meta:
        ordering = ["-created_at"]
        unique_together = ["owner", "name"]
```

**Checklist modelli:**
- [ ] Estende `OwnedModel, TimeStampedModel`
- [ ] `unique_together` con `owner` dove necessario
- [ ] Indici sui campi di query frequenti
- [ ] `__str__` definito
- [ ] `makemigrations && migrate`

### 3. Forms (`forms.py`)
- [ ] `ModelForm` con `Meta.fields` esplicito
- [ ] `__init__` accetta `owner` via `kwargs.pop("owner")`
- [ ] `clean_*` per validazioni custom
- [ ] Widget appropriati per date, select, textarea

### 4. Views (`views.py`)
```python
from django.contrib.auth.decorators import login_required

@login_required
def my_view(request):
    items = MyModel.objects.filter(owner=request.user)  # ALWAYS filter!
    return render(request, "app/template.html", {"items": items})
```

**Checklist views:**
- [ ] `@login_required` su OGNI view
- [ ] Query sempre filtrate per `owner=request.user`
- [ ] `get_object_or_404(Model, id=..., owner=request.user)`
- [ ] `item.owner = request.user` prima del save
- [ ] Redirect dopo POST (pattern PRG)

### 5. URLs (`urls.py`)
- [ ] Route registrate in `mio_master/urls.py` o nell'`urls.py` dell'app
- [ ] `name=` univoco e descrittivo (es. `projects-timeline`)
- [ ] Pattern: `/app/azione` (no underscore, no trattini nell'azione)

### 6. Templates (`templates/app/`)
```html
{% extends "app/base.html" %}
{% load static %}

{% block content %}
  <form hx-post="/url/" hx-target="#result" hx-swap="innerHTML">
    {% csrf_token %}
    <input name="field" class="uk-input">
    <button class="uk-button uk-button-primary">
      <span class="htmx-indicator" uk-spinner></span>
      <span class="btn-text">Save</span>
    </button>
  </form>
{% endblock %}
```

**Checklist template:**
- [ ] `{% csrf_token %}` in OGNI form
- [ ] Form POST/HTMX con `hx-target` e `hx-swap` espliciti
- [ ] `htmx-indicator` con spinner su azioni che chiamano il server
- [ ] Classi UIKit (`uk-card`, `uk-button`, `uk-grid`, `uk-input`, `uk-label`)
- [ ] Estende `base.html` con `{% block extra_head %}` per CSS extra

### 7. Statici — Stimulus Controller
```javascript
import { registerStimulusController, withStimulusModule } from "@core/stimulus.js";

withStimulusModule(({ Controller }) => {
  class MyController extends Controller {
    static targets = ["input"];
    connect() { /* init */ }
    action(event) {
      event.preventDefault();
      // logic
    }
  }
  registerStimulusController("my-controller", MyController);
});
```

**File location:** `core/static/core/<feature>.js` (entrypoint per Vite)

**Checklist Stimulus:**
- [ ] Nome controller in kebab-case (`data-controller="my-feature"`)
- [ ] Target dichiarati con `static targets`
- [ ] Azioni con `data-action="event->controller#method"`
- [ ] `registerStimulusController` chiamato a fine file

### 8. Bundle Vite (`vite.config.mjs`)
- [ ] Aggiunto entry in `rollupOptions.input`
- [ ] Path: `resolvePath("core/static/core/<feature>.js")`

### 9. Stili (`core/static/core/styles/`)
- [ ] Nuovi stili in `12-app-projects.less` (o file dedicato se nuova app)
- [ ] Se nuovo file, importarlo in `core/static/core/styles.less`
- [ ] Seguire convenzione BEM-like: `.shell`, `.shell-head`, `.kpi-card`, `.kpi-label`, `.kpi-value`
- [ ] Usare variabili CSS esistenti (`var(--bg)`, `var(--ink)`, `var(--muted)`, `var(--accent)`)
- [ ] Breakpoint responsive: 960px, 760px, 640px

### 10. Build & Verifica
```bash
pnpm build                    # compila bundle JS
python manage.py check        # check Django sistema
python manage.py test <app>   # test specifici
```

---

## Pattern di Scelta UI

### Quando usare Full Page (render tradizionale)
- Pagina completamente nuova (dashboard, vista dedicata)
- Contenuto che cambia radicalmente struttura
- Navigazione primaria

### Quando usare HTMX Partial
- Aggiornamento di una porzione di pagina senza reload
- Filtri, board, liste che cambiano dati ma non layout
- Form che sostituiscono se stessi dopo submit
- Pattern: `hx-post`, `hx-target="#id"`, `hx-swap="outerHTML"`

### Quando usare Stimulus Controller
- Interattività client-side senza chiamata server (tabs, accordion, toggle)
- Integrazione con librerie JS (Quill editor, chart, Gantt)
- Debounce/throttle su input
- Animazioni e transizioni UI
- Gestione stato locale effimero

### Decision Tree
```
La feature richiede round-trip server?
├── Sì → Usa HTMX (hx-get/hx-post + partial template)
│   └── Se il partial ha interattività aggiuntiva → aggiungi data-controller
└── No → Usa Stimulus (data-controller + data-action)
    └── Se è una libreria esterna → Stimulus come wrapper (init in connect())
```

---

## Convenzioni di Naming

### File
| Cosa | Dove | Esempio |
|------|------|---------|
| Nuova view | `<app>/views.py` o `<app>/<feature>_views.py` se molte righe | `timeline_views.py` |
| Nuovo form | `<app>/forms.py` o `<app>/<feature>_forms.py` | `storyboard_forms.py` |
| Template pagina | `<app>/templates/<app>/<nome>.html` | `projects/timeline.html` |
| Partial HTMX | `<app>/templates/<app>/partials/<nome>.html` | `partials/storyboard_log.html` |
| Stimulus entry | `core/static/core/<feature>.js` | `projects_timeline.js` |
| Stili feature | `core/static/core/styles/<NN>-app-<nome>.less` | `12-app-projects.less` |

### CSS Classi (BEM-like per lo scope dell'app)
```
<app>-shell          → contenitore principale della pagina
<app>-shell-head     → header con titolo e azioni
<app>-kicker         → sopra-titolo uppercase
<app>-kpi-card       → card metrica
<app>-kpi-label      → etichetta metrica
<app>-kpi-value      → valore metrica
<app>-panel          → pannello laterale
<app>-panel-head     → header del pannello
<app>-log-list       → lista di elementi
<app>-log-item       → singolo elemento lista
<app>-log-head       → header elemento (label + data)
<app>-log-title      → titolo elemento
<app>-filter-form    → form filtri
<app>-filter-chips   → chip filtro (bottoni pill)
<app>-filter-row     → riga form filtri
```

### URL Pattern
```
/app/                → dashboard
/app/view            → dettaglio (con ?id=)
/app/api/add         → creazione
/app/api/update      → modifica (con ?id=)
/app/api/remove      → rimozione (con ?id=)
/app/<feature>       → feature aggiuntiva
/app/<feature>/data  → endpoint JSON/partial
```

---

## Cross-App Integration

### Contatti (`contacts`)
- `sync_contacts_from_legacy(owner)` — da chiamare prima di usare contatti come choices
- `upsert_contact(owner, name, entity_type, roles)` — crea o aggiorna contatto
- `ensure_legacy_records_for_contact(contact)` — allinea Customer/Payee/IncomeSource legacy

### Finance Hub (`finance_hub`)
- `QuoteForm`, `QuoteLineFormSet` — riusabili da `projects` per preventivi
- `VatCode` — codici IVA, da pre-popolare con `_ensure_default_vat_codes(user)`

### Todo / Planner / Routines / Transactions
- Tutti linkabili a `Project` via FK `project`
- Query sempre filtrate per `owner=request.user` E `project=project`

---

## Checklist Pre-Commit

Prima di considerare completata una feature:

### Codice
- [ ] `@login_required` su tutte le view
- [ ] `{% csrf_token %}` in tutti i form POST
- [ ] Query filtrate per `owner=request.user`
- [ ] `item.owner = request.user` prima del `.save()`
- [ ] Nessun import da layer superiore (L3 non importa L4)

### Frontend
- [ ] `pnpm build` completa senza errori
- [ ] Bundle JS aggiunto a `vite.config.mjs`
- [ ] Stili aggiunti al file `.less` corretto e importati
- [ ] Template carica il bundle con `<script type="module">`
- [ ] HTMX indicator presente su azioni server

### Qualità
- [ ] `python manage.py check` passa (se DB disponibile)
- [ ] `python -c "import ast; ast.parse(open('file.py').read())"` su tutti i file Python
- [ ] Nessun `print()` di debug lasciato
- [ ] Nessun commento superfluo (il codice è auto-documentante)

---

## Errori Comuni da Evitare

1. **Dimenticare `owner` nel contesto** — ogni record è scoped per utente
2. **Form senza `{% csrf_token %}`** — Django blocca la richiesta
3. **Query senza filtro owner** — potenziale data leak tra utenti
4. **Import da layer sbagliato** — L2 non importa mai da L3 o L4
5. **Template senza `hx-target`** — HTMX non sa dove mettere la risposta
6. **Bundle non aggiunto a vite.config.mjs** — file non compilato
7. **Path assoluti invece di `resolvePath`** — build Vite fallisce
8. **Dimenticare `migrate` dopo nuovi modelli** — il DB non ha la tabella
9. **Stili non importati in `styles.less`** — CSS non caricato
10. **`id` passato come stringa invece di int** — `get_object_or_404` fallisce

---

## Esempio Completo: Feature "Timeline Progetti"

```
1. Analisi
   Layer: L2 (projects)
   Modelli esistenti: Project, SubProject, Task (todo), PlannerItem (planner)
   Pattern UI: Full page + Stimulus Gantt (SVG rendering client-side)

2. timeline_views.py
   - timeline_dashboard(request) → render pagina con dati JSON
   - timeline_data(request) → JsonResponse con dati timeline

3. urls.py
   - path('timeline', ...)
   - path('timeline/data', ...)

4. templates/projects/timeline.html
   - Estende projects/base.html
   - KPI cards, scope filter, toolbar zoom
   - Div container per Gantt con data-controller
   - json_script per passare dati al controller

5. core/static/core/projects_timeline.js
   - Stimulus controller: ProjectsTimelineController
   - SVG rendering: barre colorate, today marker, zoom
   - Target: canvas, svg

6. vite.config.mjs
   - Aggiunto: projects_timeline: resolvePath("core/static/core/projects_timeline.js")

7. styles/12-app-projects.less
   - Aggiunte classi: .timeline-shell, .timeline-gantt, .timeline-gantt-canvas, etc.

8. projects/templates/projects/base.html
   - Aggiunto tab "Timeline" nella nav

9. Build
   pnpm build → OK
   python manage.py check → OK (se DB disponibile)
```
