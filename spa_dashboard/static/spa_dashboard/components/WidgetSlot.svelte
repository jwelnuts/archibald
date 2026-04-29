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
