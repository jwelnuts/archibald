# SPA Dashboard — Layout Principale (Header + Toolbar) Design

## Goal

Aggiungere alla SPA dashboard Svelte 5 un layout a tre righe con header fisso in cima e toolbar fissa in fondo, stile Windows taskbar. L'area centrale rimane scrollabile e contiene la widget grid esistente.

## Visual Style

**Palette Neutral — Sabbia/Ambra:**
- Background header/toolbar: `#1c1917` (marrone scuro warm)
- Background content area: `#f0ede8` (sabbia)
- Widget background: `#faf8f5`
- Accento primario: `#f59e0b` (ambra)
- Testo primario header: `#fef3c7` (crema chiaro)
- Testo secondario: `#9d8b7a` (grigio warm)
- Bordi: `#2c2420`
- Connessione online: `#22c55e` (verde)
- Connessione offline: `#ef4444` (rosso)

## Struttura Layout

`App.svelte` usa CSS Grid a 3 righe:

```css
.spa-dashboard {
  display: grid;
  grid-template-rows: auto 1fr auto;
  height: 100dvh;
  overflow: hidden;
}
```

- **Riga 1 (auto):** `AppHeader` — altezza naturale, non scrolla
- **Riga 2 (1fr):** `<main>` con `overflow-y: auto` — unica zona scrollabile
- **Riga 3 (auto):** `AppToolbar` — altezza naturale, sempre visibile

Nessun `position: fixed` — il grid gestisce tutto.

## File Structure

| File | Azione | Responsabilità |
|------|--------|----------------|
| `spa_dashboard/static/spa_dashboard/components/AppHeader.svelte` | Crea | Header fisso: logo, clock, connessione, avatar |
| `spa_dashboard/static/spa_dashboard/components/AppToolbar.svelte` | Crea | Toolbar fissa: app links, + Nuovo, notifiche, settings |
| `spa_dashboard/static/spa_dashboard/App.svelte` | Modifica | Aggiunge grid layout, importa AppHeader e AppToolbar |
| `spa_dashboard/templates/spa_dashboard/shell.html` | Modifica | Aggiunge `window.__USER__` con nome utente dal context Django |
| `spa_dashboard/views.py` | Modifica | Passa `user_display_name` al template shell |

## AppHeader

### Aspetto

```
┌─────────────────────────────────────────────────────┐
│ ◆ MI.Organizzo          mer 29 apr · 14:32  ● R    │
└─────────────────────────────────────────────────────┘
```

- Background: `#1c1917`
- Altezza: `48px`
- Padding: `0 1.5rem`

### Contenuto

**Sinistra:**
- Punto ambra `◆` + testo "MI.Organizzo" in `#f59e0b`, font-weight 700

**Destra (da sx a dx):**
- Data e ora: aggiornate ogni 60s via `setInterval` in `onMount`/`onDestroy`
- Separatore verticale `1px solid #2c2420`
- Indicatore connessione: cerchio `8px`, verde `#22c55e` se online, rosso `#ef4444` se offline. Stato gestito con `navigator.onLine` + listener `online`/`offline` su `window`
- Avatar: cerchio `32px`, background `#2c2420`, iniziale utente in ambra. Nome da `window.__USER__.initials`

### Props

Nessuna prop — gestisce internamente clock e stato connessione.

### Dati utente

`shell.html` espone:
```html
<script>
  window.__CSRF__ = "{{ csrf_token }}";
  window.__USER__ = { name: "{{ user_display_name }}", initials: "{{ user_initials }}" };
</script>
```

`views.py` calcola `user_display_name` (first_name se presente, altrimenti username) e `user_initials` (prima lettera maiuscola di `user_display_name`, una sola lettera).

## AppToolbar

### Aspetto

```
┌─────────────────────────────────────────────────────┐
│ [📅][📁][✅][💰][🧠]  │  [+ Nuovo]  │  [🔔][⚙️]  │
└─────────────────────────────────────────────────────┘
```

- Background: `#1c1917`
- Altezza: `44px`
- Padding: `0 1rem`
- Tre zone: flex con `justify-content: space-between`

### Zone

**Sinistra — App links:**
Link `<a href>` verso le sezioni principali, ognuno come icona `26×26px` su `background: #2c2420`, border-radius `4px`. Link attivo (pagina corrente) con icona in ambra, gli altri in `#9d8b7a`.

| Icona | Label | URL Django |
|-------|-------|-----------|
| 📅 | Agenda | `/agenda/` |
| 📁 | Progetti | `/projects/` |
| ✅ | Todo | `/todo/` |
| 💰 | Finanze | `/finance/` |
| 🧠 | Memoria | `/memory-stock/` |

**Centro — Azione rapida:**
Bottone `+ Nuovo` in ambra (`background: #f59e0b`, `color: #1c1917`, font-weight 700). Per ora `disabled` con `cursor: not-allowed` e opacity ridotta — placeholder per Phase 2.

**Destra — Utilità:**
- Icona notifiche 🔔 — placeholder, no-op per ora
- Icona settings ⚙️ — link a `/profile/`

### Props

Nessuna prop — links hardcoded in Phase 1.

## Modifiche ad App.svelte

```svelte
<script>
  import AppHeader from './components/AppHeader.svelte'
  import AppToolbar from './components/AppToolbar.svelte'
  // ... resto invariato
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

## CSS Reset in shell.html

Aggiungere inline in `shell.html`:
```html
<style>
  *, *::before, *::after { box-sizing: border-box; }
  body { margin: 0; padding: 0; }
</style>
```

Senza questo, margin/padding di default del browser rompono il `100dvh`.

## Testing

- Aprire `/` — verificare che header e toolbar siano sempre visibili anche scrollando la widget grid
- Ridurre finestra a mobile — verificare che non si sovrappongano
- Portare il browser offline (DevTools → Network → Offline) — il pallino diventa rosso
- Verificare che il clock si aggiorni ogni minuto
