# SPA Dashboard — Design Spec
**Data:** 2026-04-29
**Fase:** 1 — Dashboard vuota con griglia widget e polling live

---

## Contesto

MI.Organizzo è un ERP personale Django con ~20 app. La homepage attuale (`/`) è una dashboard server-rendered in `core` con widget configurabili via HTMX. L'obiettivo è sostituirla con una SPA Svelte 5 che vive in tempo reale, usando i dati delle app esistenti tramite endpoint JSON dedicati. Il widget builder (fase 2) sarà costruito sopra questa base.

La fase 1 copre: app Django `spa_dashboard`, shell HTML, 3 endpoint JSON, struttura Svelte completa con griglia vuota e widget placeholder.

---

## Architettura generale

### App Django: `spa_dashboard`

- Nuova app Django separata, non dipende da `core` lato template
- Una sola view `dashboard(request)` registrata su `path('', ...)` in `mio_master/urls.py`
- La `core.dashboard` view esistente viene spostata su `/core/legacy-dashboard/` — non eliminata
- `spa_dashboard` riusa i modelli Django esistenti (Project, Task, etc.) direttamente nelle sue view
- Nessun template Django complesso: la shell è HTML statico con solo `{% csrf_token %}` e `{% static %}`

### Entry point Svelte

Nuovo entry point Vite in `vite.config.mjs`:
```
spa_dashboard: resolvePath("spa_dashboard/static/spa_dashboard/main.js")
```

Output compilato in `spa_dashboard/static/spa_dashboard/dist/`.

---

## Struttura file

### Backend
```
spa_dashboard/
  __init__.py
  apps.py
  views.py          ← shell view + 3 endpoint JSON
  widget_data.py    ← fetcher per tipo widget (funzioni pure)
  urls.py
  templates/
    spa_dashboard/
      shell.html
```

### Frontend
```
spa_dashboard/static/spa_dashboard/
  main.js               ← monta Svelte su #app
  App.svelte            ← root: orchestrazione fetch, polling, stato
  lib/
    api.js              ← fetch wrapper (fetchLayout, saveLayout, fetchWidgetData)
    store.svelte.js     ← $state globale: layout, widgetData, widgetStatus
  components/
    WidgetGrid.svelte   ← CSS Grid a 12 colonne
    WidgetSlot.svelte   ← singolo slot con skeleton loader
    WidgetPlaceholder.svelte ← widget vuoto fase 1
  dist/                 ← output Vite (gitignored)
```

---

## Shell HTML

```html
<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MI.Organizzo</title>
  <!-- CSS generato da Vite solo se main.js importa un file .css o .svelte con <style> -->
  <!-- In fase 1 gli stili sono inline nei componenti Svelte; aggiungere questo tag quando necessario -->
  <!-- <link rel="stylesheet" href="{% static 'spa_dashboard/dist/spa_dashboard.css' %}"> -->
  <script>window.__CSRF__ = "{{ csrf_token }}";</script>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="{% static 'spa_dashboard/dist/spa_dashboard.js' %}"></script>
</body>
</html>
```

Niente nav Django, niente base template. Svelte gestisce l'intero DOM incluso eventuale nav futuro.

---

## Endpoint JSON

Tutti in `spa_dashboard/views.py`, autenticazione via session cookie Django, CSRF via header `X-CSRFToken`.

### `GET /api/spa/layout`

Ritorna il layout salvato in `UserNavConfig.config["spa_layout"]`. Se non esiste, ritorna un default con 3 placeholder.

```json
{
  "layout": [
    {"id": "w1", "type": "placeholder", "col_span": 4, "row_span": 1},
    {"id": "w2", "type": "placeholder", "col_span": 4, "row_span": 1},
    {"id": "w3", "type": "placeholder", "col_span": 4, "row_span": 1}
  ]
}
```

### `POST /api/spa/layout`

Salva `layout` (array di slot) in `UserNavConfig.config["spa_layout"]`.

Request body: `{"layout": [...]}`
Response: `{"ok": true}`
Errori: `{"ok": false, "error": "invalid_payload"}` (400)

### `GET /api/spa/widget/<widget_id>/data`

Django legge il tipo widget dal layout salvato, chiama il fetcher corrispondente in `widget_data.py`, ritorna il JSON.

Per `placeholder`: ritorna `{}`
Response wrapper: `{"widget_id": "w1", "type": "placeholder", "data": {}}`
Errori: 404 se `widget_id` non trovato nel layout, 401 se non autenticato.

---

## `widget_data.py`

Ogni fetcher è una funzione pura che riceve `(user, slot)` e ritorna un dict serializzabile:

```python
WIDGET_FETCHERS = {
    "placeholder": lambda user, slot: {},
}

def fetch_widget_data(user, slot):
    fetcher = WIDGET_FETCHERS.get(slot["type"])
    if fetcher is None:
        return {}
    return fetcher(user, slot)
```

Quando arriveranno widget reali (es. `projects_kpi`, `todo_open`), si aggiunge la chiave al dict senza toccare il resto.

---

## Stato Svelte (`store.svelte.js`)

```js
// layout: array ordinato di slot, caricato da /api/spa/layout
export let layout = $state([])

// dati per widget, keyed per widget id
export let widgetData = $state({})

// stato fetch per widget: 'loading' | 'ok' | 'error'
export let widgetStatus = $state({})
```

---

## `api.js`

```js
const CSRF = window.__CSRF__

export async function fetchLayout() {
  const res = await fetch('/api/spa/layout')
  return res.json()
}

export async function saveLayout(layout) {
  const res = await fetch('/api/spa/layout', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
    body: JSON.stringify({ layout })
  })
  return res.json()
}

export async function fetchWidgetData(widgetId) {
  const res = await fetch(`/api/spa/widget/${widgetId}/data`)
  return res.json()
}
```

Niente librerie HTTP — `fetch` nativo.

---

## `App.svelte` — ciclo di vita

1. `onMount` → `fetchLayout()` → popola `layout`
2. Per ogni slot in `layout`: imposta `widgetStatus[id] = 'loading'`, chiama `fetchWidgetData(id)`, popola `widgetData[id]`, imposta `widgetStatus[id] = 'ok'` (o `'error'`)
3. `setInterval(refreshAll, 30000)` — rilancia tutti i fetch ogni 30 secondi
4. `onDestroy` → `clearInterval`

---

## `WidgetGrid.svelte`

CSS Grid a 12 colonne. Ogni slot usa `grid-column: span {col_span}`:

```svelte
<div class="widget-grid">
  {#each layout as slot (slot.id)}
    <WidgetSlot {slot} />
  {/each}
</div>

<style>
.widget-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 1rem;
}
</style>
```

Mobile (< 768px): `grid-template-columns: 1fr` — tutti i widget a piena larghezza.

---

## `WidgetSlot.svelte`

Riceve `slot` come prop. Legge `widgetStatus` e `widgetData` dallo store. Mostra skeleton loader durante `'loading'`, componente widget durante `'ok'`, messaggio errore durante `'error'`.

Seleziona il componente widget dinamicamente con `<svelte:component this={widgetComponent}>` basandosi su `slot.type`.

---

## `WidgetPlaceholder.svelte`

Riquadro con bordo tratteggiato, testo centrato "Widget vuoto". Usato per tutti gli slot nella fase 1. Nessun dato richiesto.

---

## Griglia CSS — dettaglio

```css
.widget-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 1rem;
  padding: 1rem;
}

/* applicato inline da WidgetSlot */
/* style="grid-column: span {slot.col_span}; grid-row: span {slot.row_span}" */

@media (max-width: 768px) {
  .widget-grid {
    grid-template-columns: 1fr;
  }
}
```

---

## Vite — entry point

In `vite.config.mjs`, aggiungere alle `input`:
```js
spa_dashboard: resolvePath("spa_dashboard/static/spa_dashboard/main.js"),
```

Svelte va installato come devDependency:
```
pnpm add -D svelte @sveltejs/vite-plugin-svelte
```

E il plugin aggiunto alla config Vite:
```js
import { svelte } from '@sveltejs/vite-plugin-svelte'
// plugins: [svelte()]
```

---

## `mio_master/urls.py` — cambio root

`core.urls` contiene endpoint critici (`/accounts/login/`, `/api/mobile/`, `/profile/`, etc.) che devono restare invariati. Si aggiunge solo `spa_dashboard.urls` prima di `core.urls`, e si aggiunge un alias per la legacy dashboard direttamente in `core.urls`:

```python
# mio_master/urls.py
path('', include('spa_dashboard.urls')),   # nuova SPA su /
path('', include('core.urls')),            # core resta invariato (login, api, profile...)
```

```python
# core/urls.py — aggiungere alias
path('core/legacy-dashboard/', views.dashboard, name='core-legacy-dashboard'),
# lasciare path('', views.dashboard, ...) — verrà oscurato da spa_dashboard che viene prima
```

---

## Cosa NON è in scope per la fase 1

- Widget con dati reali (KPI, tabelle, grafici)
- Nav/menu Svelte
- Autenticazione gestita da Svelte (usa session Django esistente)
- Widget builder
- Drag & drop
- Animazioni di transizione

---

## Criteri di successo fase 1

1. `GET /` ritorna la shell HTML con `<div id="app">`
2. Svelte monta, fa fetch a `/api/spa/layout`, renderizza 3 WidgetPlaceholder in griglia
3. Il polling ogni 30s non genera errori in console
4. Il layout default viene salvato correttamente in `UserNavConfig` al primo accesso
5. La `core.dashboard` legacy è ancora accessibile su `/core/legacy-dashboard/`
