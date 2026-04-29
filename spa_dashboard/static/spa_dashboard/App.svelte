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
