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
