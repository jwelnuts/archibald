# SPA Dashboard Phase 1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Creare la nuova app Django `spa_dashboard` su `/` con una SPA Svelte 5 che monta una griglia vuota di widget placeholder con polling live ogni 30 secondi.

**Architecture:** App Django `spa_dashboard` serve una shell HTML minimale su `/`. Svelte 5 monta su `#app`, fa fetch a tre endpoint JSON (`/api/spa/layout`, `POST /api/spa/layout`, `/api/spa/widget/<id>/data`), e renderizza una CSS Grid 12 colonne con `WidgetPlaceholder`. Il layout è persistito in `UserNavConfig.config["spa_layout"]`. Il polling aggiorna i dati ogni 30s via `setInterval`.

**Tech Stack:** Django 4+, Svelte 5 (rune: `$state`, `$derived`, `$props`), Vite 6 + `@sveltejs/vite-plugin-svelte`, `fetch` nativo, CSS Grid, pnpm.

---

## File Map

**Nuovi file backend:**
- `spa_dashboard/__init__.py`
- `spa_dashboard/apps.py`
- `spa_dashboard/urls.py`
- `spa_dashboard/views.py` — shell view + 3 endpoint JSON
- `spa_dashboard/widget_data.py` — fetcher per tipo widget
- `spa_dashboard/templates/spa_dashboard/shell.html`

**Nuovi file frontend:**
- `spa_dashboard/static/spa_dashboard/main.js`
- `spa_dashboard/static/spa_dashboard/App.svelte`
- `spa_dashboard/static/spa_dashboard/lib/api.js`
- `spa_dashboard/static/spa_dashboard/lib/store.svelte.js`
- `spa_dashboard/static/spa_dashboard/components/WidgetGrid.svelte`
- `spa_dashboard/static/spa_dashboard/components/WidgetSlot.svelte`
- `spa_dashboard/static/spa_dashboard/components/WidgetPlaceholder.svelte`

**File modificati:**
- `mio_master/settings.py` — aggiunge `spa_dashboard` a `INSTALLED_APPS`
- `mio_master/urls.py` — antepone `spa_dashboard.urls` a `core.urls`
- `core/urls.py` — aggiunge alias `/core/legacy-dashboard/`
- `vite.config.mjs` — aggiunge entry point + plugin Svelte

---

## Task 1: Installare Svelte e configurare Vite

**Files:**
- Modify: `vite.config.mjs`
- Modify: `package.json` (via pnpm)

- [ ] **Step 1: Installare dipendenze Svelte**

```bash
cd /home/bubbaman/Dev/miorganizzo/mio_master
pnpm add -D svelte @sveltejs/vite-plugin-svelte
```

Expected output: pacchetti installati, `pnpm-lock.yaml` aggiornato.

- [ ] **Step 2: Aggiornare `vite.config.mjs`**

Contenuto completo del file dopo la modifica:

```js
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const resolvePath = (...parts) => path.resolve(__dirname, ...parts);

export default defineConfig({
  plugins: [svelte()],
  resolve: {
    alias: {
      "@core": resolvePath("core/static/core"),
    },
  },
  build: {
    outDir: resolvePath("core/static/core/dist"),
    emptyOutDir: true,
    sourcemap: true,
    rollupOptions: {
      input: {
        app: resolvePath("core/static/core/app.js"),
        dashboard: resolvePath("core/static/core/dashboard.js"),
        transactions: resolvePath("core/static/core/transactions.js"),
        todo: resolvePath("core/static/core/todo.js"),
        routines: resolvePath("core/static/core/todos.js"),
        projects_storyboard: resolvePath("core/static/core/projects_storyboard.js"),
        agenda: resolvePath("agenda/static/agenda/agenda.js"),
        subscriptions_dashboard: resolvePath("subscriptions/static/subscriptions/dashboard.js"),
        spa_dashboard: resolvePath("spa_dashboard/static/spa_dashboard/main.js"),
      },
      output: {
        format: "es",
        entryFileNames: "[name].js",
        chunkFileNames: "chunks/[name].js",
        assetFileNames: "assets/[name][extname]",
      },
    },
  },
});
```

- [ ] **Step 3: Verificare che il build non esploda (il file main.js non esiste ancora — è ok)**

```bash
pnpm run build 2>&1 | grep -E "error|Error|spa_dashboard" | head -20
```

Expected: errore su `spa_dashboard/static/spa_dashboard/main.js` non trovato — normale, lo creiamo nel Task 3. Gli altri entry point devono compilare senza errori.

- [ ] **Step 4: Commit**

```bash
git add vite.config.mjs pnpm-lock.yaml package.json
git commit -m "feat: add svelte vite plugin and spa_dashboard entry point"
```

---

## Task 2: Creare l'app Django `spa_dashboard`

**Files:**
- Create: `spa_dashboard/__init__.py`
- Create: `spa_dashboard/apps.py`
- Create: `spa_dashboard/widget_data.py`
- Create: `spa_dashboard/urls.py`
- Create: `spa_dashboard/views.py`
- Create: `spa_dashboard/templates/spa_dashboard/shell.html`
- Modify: `mio_master/settings.py`
- Modify: `mio_master/urls.py`
- Modify: `core/urls.py`

- [ ] **Step 1: Creare la struttura directory**

```bash
mkdir -p spa_dashboard/templates/spa_dashboard
touch spa_dashboard/__init__.py
```

- [ ] **Step 2: Creare `spa_dashboard/apps.py`**

```python
from django.apps import AppConfig


class SpaDashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "spa_dashboard"
```

- [ ] **Step 3: Creare `spa_dashboard/widget_data.py`**

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

- [ ] **Step 4: Creare `spa_dashboard/views.py`**

```python
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from core.models import UserNavConfig
from .widget_data import fetch_widget_data

DEFAULT_LAYOUT = [
    {"id": "w1", "type": "placeholder", "col_span": 4, "row_span": 1},
    {"id": "w2", "type": "placeholder", "col_span": 4, "row_span": 1},
    {"id": "w3", "type": "placeholder", "col_span": 4, "row_span": 1},
]


def _get_spa_layout(user):
    nav_config = UserNavConfig.objects.filter(user=user).first()
    if nav_config and isinstance(nav_config.config, dict):
        saved = nav_config.config.get("spa_layout")
        if isinstance(saved, list) and saved:
            return saved
    return DEFAULT_LAYOUT


def _save_spa_layout(user, layout):
    nav_config, _ = UserNavConfig.objects.get_or_create(user=user)
    config = nav_config.config if isinstance(nav_config.config, dict) else {}
    config["spa_layout"] = layout
    nav_config.config = config
    nav_config.save(update_fields=["config"])


@login_required
def shell(request):
    return render(request, "spa_dashboard/shell.html")


@login_required
@require_http_methods(["GET"])
def api_layout_get(request):
    layout = _get_spa_layout(request.user)
    return JsonResponse({"layout": layout})


@login_required
@require_http_methods(["POST"])
def api_layout_save(request):
    try:
        payload = json.loads((request.body or b"{}").decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    layout = payload.get("layout")
    if not isinstance(layout, list):
        return JsonResponse({"ok": False, "error": "invalid_payload"}, status=400)

    for slot in layout:
        if not isinstance(slot, dict) or "id" not in slot or "type" not in slot:
            return JsonResponse({"ok": False, "error": "invalid_slot"}, status=400)

    _save_spa_layout(request.user, layout)
    return JsonResponse({"ok": True})


@login_required
@require_http_methods(["GET"])
def api_widget_data(request, widget_id):
    layout = _get_spa_layout(request.user)
    slot = next((s for s in layout if s["id"] == widget_id), None)
    if slot is None:
        return JsonResponse({"error": "not_found"}, status=404)

    data = fetch_widget_data(request.user, slot)
    return JsonResponse({"widget_id": widget_id, "type": slot["type"], "data": data})
```

- [ ] **Step 5: Creare `spa_dashboard/urls.py`**

```python
from django.urls import path
from . import views

urlpatterns = [
    path("", views.shell, name="spa-dashboard-shell"),
    path("api/spa/layout", views.api_layout_get, name="spa-layout-get"),
    path("api/spa/layout/save", views.api_layout_save, name="spa-layout-save"),
    path("api/spa/widget/<str:widget_id>/data", views.api_widget_data, name="spa-widget-data"),
]
```

- [ ] **Step 6: Creare `spa_dashboard/templates/spa_dashboard/shell.html`**

```html
{% load static %}
<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MI.Organizzo</title>
  <script>window.__CSRF__ = "{{ csrf_token }}";</script>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="{% static 'core/dist/spa_dashboard.js' %}"></script>
</body>
</html>
```

Nota: il bundle Vite finisce in `core/static/core/dist/` per via di `outDir` in `vite.config.mjs`.

- [ ] **Step 7: Aggiungere `spa_dashboard` a `INSTALLED_APPS` in `mio_master/settings.py`**

Trovare la lista `INSTALLED_APPS` e aggiungere `'spa_dashboard'` subito dopo `'core.apps.CoreConfig'`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core.apps.CoreConfig',
    'spa_dashboard',           # ← aggiunto
    'projects',
    # ... resto invariato
]
```

- [ ] **Step 8: Aggiornare `mio_master/urls.py`**

Aggiungere `spa_dashboard.urls` come prima entry, mantenendo tutto il resto:

```python
from django.contrib import admin
from django.urls import include, path
from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('media/<path:path>', core_views.protected_media, name='protected-media'),

    path('', include('spa_dashboard.urls')),   # ← SPA prima di core
    path('', include('core.urls')),
    path('subs/', include('finance_hub.urls')),
    path('projects/', include('projects.urls')),
    path('todo/', include('todo.urls')),
    path('agenda/', include('agenda.urls')),
    path('workbench/', include('workbench.urls')),
    path('transactions/', include('transactions.urls')),
    path('planner/', include('planner.urls')),
    path('routines/', include('todos.urls')),
    path('archibald/', include('archibald.urls')),
    path('archibald-mail/', include('archibald_mail.urls')),
    path('memory-stock/', include('memory_stock.urls')),
    path('vault/', include('vault.urls')),
    path('finance/', include('finance_hub.urls')),
    path('link_storage/', include('link_storage.urls')),
    path('contacts/', include('contacts.urls')),
]
```

- [ ] **Step 9: Aggiungere alias legacy in `core/urls.py`**

Aggiungere questa riga alla lista `urlpatterns` in `core/urls.py`:

```python
path('core/legacy-dashboard/', views.dashboard, name='core-legacy-dashboard'),
```

- [ ] **Step 10: Verificare che Django si avvii senza errori**

```bash
python manage.py check 2>&1
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 11: Verificare gli endpoint con curl (server deve girare)**

```bash
python manage.py runserver &
sleep 2
curl -s http://localhost:8000/ | grep -c "div id=\"app\""
# Expected: 1 (redirect a login se non autenticato — ok)
kill %1
```

- [ ] **Step 12: Commit**

```bash
git add spa_dashboard/ mio_master/settings.py mio_master/urls.py core/urls.py
git commit -m "feat: add spa_dashboard Django app with shell and JSON endpoints"
```

---

## Task 3: Creare la struttura Svelte frontend

**Files:**
- Create: `spa_dashboard/static/spa_dashboard/main.js`
- Create: `spa_dashboard/static/spa_dashboard/App.svelte`
- Create: `spa_dashboard/static/spa_dashboard/lib/api.js`
- Create: `spa_dashboard/static/spa_dashboard/lib/store.svelte.js`
- Create: `spa_dashboard/static/spa_dashboard/components/WidgetGrid.svelte`
- Create: `spa_dashboard/static/spa_dashboard/components/WidgetSlot.svelte`
- Create: `spa_dashboard/static/spa_dashboard/components/WidgetPlaceholder.svelte`

- [ ] **Step 1: Creare le directory**

```bash
mkdir -p spa_dashboard/static/spa_dashboard/lib
mkdir -p spa_dashboard/static/spa_dashboard/components
```

- [ ] **Step 2: Creare `spa_dashboard/static/spa_dashboard/lib/api.js`**

```js
const CSRF = window.__CSRF__

export async function fetchLayout() {
  const res = await fetch('/api/spa/layout')
  if (!res.ok) throw new Error(`fetchLayout failed: ${res.status}`)
  return res.json()
}

export async function saveLayout(layout) {
  const res = await fetch('/api/spa/layout/save', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': CSRF,
    },
    body: JSON.stringify({ layout }),
  })
  if (!res.ok) throw new Error(`saveLayout failed: ${res.status}`)
  return res.json()
}

export async function fetchWidgetData(widgetId) {
  const res = await fetch(`/api/spa/widget/${widgetId}/data`)
  if (!res.ok) throw new Error(`fetchWidgetData failed: ${res.status}`)
  return res.json()
}
```

- [ ] **Step 3: Creare `spa_dashboard/static/spa_dashboard/lib/store.svelte.js`**

```js
export let layout = $state([])
export let widgetData = $state({})
export let widgetStatus = $state({})
```

- [ ] **Step 4: Creare `spa_dashboard/static/spa_dashboard/components/WidgetPlaceholder.svelte`**

```svelte
<script>
  let { slot } = $props()
</script>

<div class="widget-placeholder">
  <span class="widget-placeholder-label">Widget vuoto</span>
  <span class="widget-placeholder-sub">({slot.col_span}×{slot.row_span})</span>
</div>

<style>
  .widget-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 120px;
    border: 2px dashed #ccc;
    border-radius: 8px;
    background: #fafafa;
    gap: 4px;
  }

  .widget-placeholder-label {
    font-size: 0.85rem;
    color: #999;
    font-weight: 500;
  }

  .widget-placeholder-sub {
    font-size: 0.75rem;
    color: #bbb;
  }
</style>
```

- [ ] **Step 5: Creare `spa_dashboard/static/spa_dashboard/components/WidgetSlot.svelte`**

```svelte
<script>
  import { widgetData, widgetStatus } from '../lib/store.svelte.js'
  import WidgetPlaceholder from './WidgetPlaceholder.svelte'

  const WIDGET_COMPONENTS = {
    placeholder: WidgetPlaceholder,
  }

  let { slot } = $props()

  let status = $derived(widgetStatus[slot.id] ?? 'loading')
  let data = $derived(widgetData[slot.id] ?? {})
  let WidgetComponent = $derived(WIDGET_COMPONENTS[slot.type] ?? WidgetPlaceholder)
</script>

<div
  class="widget-slot"
  style="grid-column: span {slot.col_span}; grid-row: span {slot.row_span};"
>
  {#if status === 'loading'}
    <div class="widget-skeleton"></div>
  {:else if status === 'error'}
    <div class="widget-error">Errore caricamento widget</div>
  {:else}
    <svelte:component this={WidgetComponent} {slot} {data} />
  {/if}
</div>

<style>
  .widget-slot {
    min-height: 120px;
  }

  .widget-skeleton {
    height: 120px;
    border-radius: 8px;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
  }

  @keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  .widget-error {
    height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid #f5c6cb;
    border-radius: 8px;
    background: #fff5f5;
    color: #c0392b;
    font-size: 0.8rem;
  }
</style>
```

- [ ] **Step 6: Creare `spa_dashboard/static/spa_dashboard/components/WidgetGrid.svelte`**

```svelte
<script>
  import { layout } from '../lib/store.svelte.js'
  import WidgetSlot from './WidgetSlot.svelte'
</script>

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
    padding: 1rem;
  }

  @media (max-width: 768px) {
    .widget-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
```

- [ ] **Step 7: Creare `spa_dashboard/static/spa_dashboard/App.svelte`**

```svelte
<script>
  import { onMount, onDestroy } from 'svelte'
  import { layout, widgetData, widgetStatus } from './lib/store.svelte.js'
  import { fetchLayout, fetchWidgetData } from './lib/api.js'
  import WidgetGrid from './components/WidgetGrid.svelte'

  let pollInterval

  async function loadWidgetData(slot) {
    widgetStatus[slot.id] = 'loading'
    try {
      const result = await fetchWidgetData(slot.id)
      widgetData[slot.id] = result.data
      widgetStatus[slot.id] = 'ok'
    } catch {
      widgetStatus[slot.id] = 'error'
    }
  }

  async function refreshAll() {
    for (const slot of layout) {
      await loadWidgetData(slot)
    }
  }

  onMount(async () => {
    try {
      const result = await fetchLayout()
      layout.splice(0, layout.length, ...result.layout)
      await refreshAll()
    } catch (e) {
      console.error('SPA Dashboard: failed to load layout', e)
    }

    pollInterval = setInterval(refreshAll, 30_000)
  })

  onDestroy(() => {
    clearInterval(pollInterval)
  })
</script>

<div class="spa-dashboard">
  <header class="spa-header">
    <h1>MI.Organizzo</h1>
  </header>
  <main>
    <WidgetGrid />
  </main>
</div>

<style>
  .spa-dashboard {
    min-height: 100vh;
    background: #f5f6fa;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }

  .spa-header {
    padding: 1rem 1.5rem;
    background: #fff;
    border-bottom: 1px solid #e8e8e8;
  }

  .spa-header h1 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: #1a1a2e;
  }

  main {
    max-width: 1400px;
    margin: 0 auto;
  }
</style>
```

- [ ] **Step 8: Creare `spa_dashboard/static/spa_dashboard/main.js`**

```js
import { mount } from 'svelte'
import App from './App.svelte'

const app = mount(App, { target: document.getElementById('app') })

export default app
```

- [ ] **Step 9: Commit**

```bash
git add spa_dashboard/static/
git commit -m "feat: add svelte spa_dashboard frontend components"
```

---

## Task 4: Build e verifica finale

**Files:**
- No nuovi file — verifica build e funzionamento end-to-end

- [ ] **Step 1: Eseguire il build Vite**

```bash
pnpm run build 2>&1
```

Expected: build completo senza errori. Deve apparire `spa_dashboard.js` nell'output:
```
core/static/core/dist/spa_dashboard.js   XX.XX kB
```

- [ ] **Step 2: Raccogliere gli static file Django**

```bash
python manage.py collectstatic --noinput 2>&1 | tail -5
```

Expected: nessun errore, file copiati.

- [ ] **Step 3: Avviare il server e verificare la shell**

```bash
python manage.py runserver &
sleep 2
curl -s -L -c /tmp/cookies.txt http://localhost:8000/ | grep "div id=\"app\""
```

Expected: redirect a `/accounts/login/` (non autenticato) oppure la shell con `<div id="app">` se loggato. Entrambi sono corretti — significa che Django risponde e la route funziona.

- [ ] **Step 4: Verificare che `/core/legacy-dashboard/` risponde**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/core/legacy-dashboard/
```

Expected: `302` (redirect a login) — conferma che la legacy dashboard esiste ancora.

- [ ] **Step 5: Verificare che gli endpoint core siano ancora raggiungibili**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/accounts/login/
```

Expected: `200` — la login page di Django è intatta.

- [ ] **Step 6: Fermare il server e commit finale**

```bash
kill %1 2>/dev/null || true
git add .
git commit -m "feat: spa_dashboard phase 1 complete — svelte shell with widget grid and polling"
```

---

## Criteri di successo

1. `pnpm run build` completa senza errori e produce `core/static/core/dist/spa_dashboard.js`
2. `python manage.py check` non riporta errori
3. `GET /` → shell HTML con `<div id="app">` (dopo login)
4. `GET /api/spa/layout` → JSON con 3 placeholder
5. `GET /api/spa/widget/w1/data` → `{"widget_id": "w1", "type": "placeholder", "data": {}}`
6. `GET /core/legacy-dashboard/` → risponde (non 404)
7. `GET /accounts/login/` → risponde `200`
8. Nel browser: Svelte monta, 3 WidgetPlaceholder visibili in griglia, console senza errori, polling attivo ogni 30s

---

## Note implementative

- **`store.svelte.js`**: le variabili `$state` esportate da moduli `.svelte.js` sono reattive globalmente in Svelte 5. Importarle nei componenti con `import { layout } from '../lib/store.svelte.js'` e modificarle direttamente (es. `layout.push(...)`) aggiorna tutti i componenti che le usano.
- **`layout.splice(0, layout.length, ...result.layout)`** in `App.svelte`: necessario perché sostituire direttamente `layout = result.layout` rompe la reattività — bisogna mutare l'array in-place.
- **`outDir`**: Vite scrive tutto in `core/static/core/dist/`, quindi il bundle `spa_dashboard.js` finisce lì. Il template `shell.html` usa `{% static 'core/dist/spa_dashboard.js' %}`.
- **URL `/api/spa/layout/save`**: la spec usava `POST /api/spa/layout` ma Django gestisce GET e POST sullo stesso path con decoratori separati in modo meno pulito. Usando `/api/spa/layout/save` per il POST si evita ambiguità.
