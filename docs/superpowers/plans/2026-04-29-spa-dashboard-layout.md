# SPA Dashboard Layout (Header + Toolbar) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aggiungere alla SPA dashboard Svelte 5 un layout a tre righe: header fisso in cima (logo + clock + indicatore connessione + avatar), toolbar fissa in fondo stile Windows taskbar (app links + azione rapida + settings), area centrale scrollabile.

**Architecture:** `App.svelte` usa `display:grid; grid-template-rows: auto 1fr auto; height:100dvh` — nessun `position:fixed`. Due nuovi componenti Svelte: `AppHeader.svelte` e `AppToolbar.svelte`. Il backend Django passa i dati utente al template come `window.__USER__`.

**Tech Stack:** Svelte 5 (runes mode), Vite 6, CSS custom (no framework), Django 4.x template context

---

## File Structure

| File | Azione |
|------|--------|
| `spa_dashboard/static/spa_dashboard/components/AppHeader.svelte` | Crea |
| `spa_dashboard/static/spa_dashboard/components/AppToolbar.svelte` | Crea |
| `spa_dashboard/static/spa_dashboard/App.svelte` | Modifica |
| `spa_dashboard/templates/spa_dashboard/shell.html` | Modifica |
| `spa_dashboard/views.py` | Modifica |

---

### Task 1: Aggiungere dati utente al template Django

**Files:**
- Modify: `spa_dashboard/views.py`
- Modify: `spa_dashboard/templates/spa_dashboard/shell.html`

Questo task espone il nome e l'iniziale dell'utente loggato a Svelte tramite `window.__USER__`.

- [ ] **Step 1: Modificare `views.py` per passare i dati utente al template**

La view `shell` attualmente chiama solo `render(request, "spa_dashboard/shell.html")`. Aggiungere il context con `user_display_name` e `user_initials`:

```python
@login_required
def shell(request):
    user = request.user
    display_name = user.first_name if user.first_name else user.username
    initials = display_name[0].upper() if display_name else "?"
    return render(request, "spa_dashboard/shell.html", {
        "user_display_name": display_name,
        "user_initials": initials,
    })
```

- [ ] **Step 2: Modificare `shell.html` per aggiungere CSS reset e `window.__USER__`**

Il file attuale è:
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

Sostituirlo interamente con:
```html
{% load static %}
<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MI.Organizzo</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; }
    body { margin: 0; padding: 0; }
  </style>
  <script>
    window.__CSRF__ = "{{ csrf_token }}";
    window.__USER__ = { name: "{{ user_display_name }}", initials: "{{ user_initials }}" };
  </script>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="{% static 'core/dist/spa_dashboard.js' %}"></script>
</body>
</html>
```

- [ ] **Step 3: Verificare nel browser**

Avviare il dev server Django (`python manage.py runserver`) e aprire `/` nel browser. Aprire la console DevTools e verificare:
```js
window.__USER__
// Expected: { name: "...", initials: "..." }  — nome del tuo utente
```

- [ ] **Step 4: Commit**

```bash
git add spa_dashboard/views.py spa_dashboard/templates/spa_dashboard/shell.html
git commit -m "feat: pass user display name and initials to SPA shell template"
```

---

### Task 2: Creare `AppHeader.svelte`

**Files:**
- Create: `spa_dashboard/static/spa_dashboard/components/AppHeader.svelte`

Header fisso in cima: logo a sinistra, clock + indicatore connessione + avatar a destra.

**Palette usata in questo file:**
- Background: `#1c1917`
- Ambra: `#f59e0b`
- Testo secondario: `#9d8b7a`
- Bordi: `#2c2420`
- Online: `#22c55e` / Offline: `#ef4444`

- [ ] **Step 1: Creare il file `AppHeader.svelte`**

```svelte
<script>
  import { onMount, onDestroy } from 'svelte'

  let dateTimeStr = $state('')
  let isOnline = $state(navigator.onLine)

  const userInitials = window.__USER__?.initials ?? '?'

  function formatDateTime() {
    const now = new Date()
    const days = ['dom', 'lun', 'mar', 'mer', 'gio', 'ven', 'sab']
    const months = ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic']
    const day = days[now.getDay()]
    const date = now.getDate()
    const month = months[now.getMonth()]
    const hours = String(now.getHours()).padStart(2, '0')
    const mins = String(now.getMinutes()).padStart(2, '0')
    return `${day} ${date} ${month} · ${hours}:${mins}`
  }

  function handleOnline() { isOnline = true }
  function handleOffline() { isOnline = false }

  let clockInterval

  onMount(() => {
    dateTimeStr = formatDateTime()
    clockInterval = setInterval(() => { dateTimeStr = formatDateTime() }, 60_000)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
  })

  onDestroy(() => {
    clearInterval(clockInterval)
    window.removeEventListener('online', handleOnline)
    window.removeEventListener('offline', handleOffline)
  })
</script>

<header class="app-header">
  <div class="header-left">
    <span class="logo-dot">◆</span>
    <span class="logo-text">MI.Organizzo</span>
  </div>
  <div class="header-right">
    <span class="datetime">{dateTimeStr}</span>
    <div class="separator"></div>
    <div class="connection-dot" class:online={isOnline} class:offline={!isOnline}></div>
    <div class="avatar">{userInitials}</div>
  </div>
</header>

<style>
  .app-header {
    height: 48px;
    background: #1c1917;
    padding: 0 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid #2c2420;
    flex-shrink: 0;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .logo-dot {
    color: #f59e0b;
    font-size: 0.75rem;
  }

  .logo-text {
    color: #f59e0b;
    font-size: 0.9rem;
    font-weight: 700;
    letter-spacing: 0.02em;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .datetime {
    color: #9d8b7a;
    font-size: 0.8rem;
  }

  .separator {
    width: 1px;
    height: 16px;
    background: #2c2420;
  }

  .connection-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .connection-dot.online {
    background: #22c55e;
  }

  .connection-dot.offline {
    background: #ef4444;
  }

  .avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #2c2420;
    color: #f59e0b;
    font-size: 0.85rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add spa_dashboard/static/spa_dashboard/components/AppHeader.svelte
git commit -m "feat: add AppHeader component with clock and connection indicator"
```

---

### Task 3: Creare `AppToolbar.svelte`

**Files:**
- Create: `spa_dashboard/static/spa_dashboard/components/AppToolbar.svelte`

Toolbar fissa in fondo: app links a sinistra, `+ Nuovo` al centro, notifiche + settings a destra.

**Palette usata in questo file:**
- Background: `#1c1917`
- Icona attiva: `#f59e0b`
- Icona inattiva: `#9d8b7a`
- Background icona: `#2c2420`
- Bottone `+ Nuovo` (disabled): `background: #2c2420`, `color: #9d8b7a`, `opacity: 0.5`

- [ ] **Step 1: Creare il file `AppToolbar.svelte`**

```svelte
<script>
  const appLinks = [
    { icon: '📅', label: 'Agenda', href: '/agenda/' },
    { icon: '📁', label: 'Progetti', href: '/projects/' },
    { icon: '✅', label: 'Todo', href: '/todo/' },
    { icon: '💰', label: 'Finanze', href: '/finance/' },
    { icon: '🧠', label: 'Memoria', href: '/memory-stock/' },
  ]
</script>

<nav class="app-toolbar">
  <div class="toolbar-left">
    {#each appLinks as link}
      <a href={link.href} class="toolbar-icon" title={link.label}>
        {link.icon}
      </a>
    {/each}
  </div>

  <div class="toolbar-center">
    <button class="btn-new" disabled>+ Nuovo</button>
  </div>

  <div class="toolbar-right">
    <button class="toolbar-icon" title="Notifiche" disabled>🔔</button>
    <a href="/profile/" class="toolbar-icon" title="Impostazioni">⚙️</a>
  </div>
</nav>

<style>
  .app-toolbar {
    height: 44px;
    background: #1c1917;
    padding: 0 1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-top: 1px solid #2c2420;
    flex-shrink: 0;
  }

  .toolbar-left,
  .toolbar-right {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .toolbar-center {
    display: flex;
    align-items: center;
  }

  .toolbar-icon {
    width: 28px;
    height: 28px;
    background: #2c2420;
    border: none;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85rem;
    color: #9d8b7a;
    text-decoration: none;
    cursor: pointer;
    padding: 0;
    transition: background 0.15s;
  }

  .toolbar-icon:hover:not([disabled]) {
    background: #3a2e28;
  }

  .toolbar-icon[disabled] {
    cursor: not-allowed;
    opacity: 0.5;
  }

  .btn-new {
    background: #2c2420;
    border: none;
    border-radius: 4px;
    color: #9d8b7a;
    font-size: 0.8rem;
    font-weight: 700;
    padding: 0.3rem 0.75rem;
    cursor: not-allowed;
    opacity: 0.5;
  }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add spa_dashboard/static/spa_dashboard/components/AppToolbar.svelte
git commit -m "feat: add AppToolbar component with app links and quick action"
```

---

### Task 4: Aggiornare `App.svelte` con il layout a 3 righe

**Files:**
- Modify: `spa_dashboard/static/spa_dashboard/App.svelte`

Questo task assembla tutto: importa i due nuovi componenti, cambia il markup e il CSS in `App.svelte`.

- [ ] **Step 1: Sostituire il contenuto di `App.svelte`**

Il file attuale ha questo markup e stile:
```svelte
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

Sostituirlo con il file completo aggiornato:

```svelte
<script>
  import { onMount, onDestroy } from 'svelte'
  import { layout, widgetData, widgetStatus } from './lib/store.svelte.js'
  import { fetchLayout, fetchWidgetData } from './lib/api.js'
  import WidgetGrid from './components/WidgetGrid.svelte'
  import AppHeader from './components/AppHeader.svelte'
  import AppToolbar from './components/AppToolbar.svelte'

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
  <AppHeader />
  <main>
    <WidgetGrid />
  </main>
  <AppToolbar />
</div>

<style>
  .spa-dashboard {
    display: grid;
    grid-template-rows: auto 1fr auto;
    height: 100dvh;
    overflow: hidden;
    background: #f0ede8;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }

  main {
    overflow-y: auto;
    padding: 1rem;
  }
</style>
```

- [ ] **Step 2: Build Vite per verificare che non ci siano errori**

```bash
pnpm build
```

Expected: nessun errore, output in `core/static/core/dist/`.

- [ ] **Step 3: Verificare nel browser**

Avviare `python manage.py runserver` e `pnpm dev` (in terminali separati), poi aprire `/`.

Verificare:
1. Header visibile in cima con logo ambra, clock e pallino verde
2. Toolbar visibile in fondo con le 5 icone app, bottone `+ Nuovo` grigio opaco, icona ⚙️
3. Scrollare la pagina — header e toolbar rimangono fermi
4. Ridurre la finestra a meno di 400px di larghezza — nessuna sovrapposizione
5. DevTools → Network → Offline — il pallino diventa rosso; tornare Online — torna verde

- [ ] **Step 4: Commit**

```bash
git add spa_dashboard/static/spa_dashboard/App.svelte
git commit -m "feat: wire up AppHeader and AppToolbar in 3-row grid layout"
```
