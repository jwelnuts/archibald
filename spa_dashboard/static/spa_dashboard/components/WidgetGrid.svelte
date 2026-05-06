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
    columns: 3;
    column-gap: 1rem;
    padding: 1rem;
  }

  @media (max-width: 1024px) {
    .widget-grid { columns: 2; }
  }

  @media (max-width: 600px) {
    .widget-grid { columns: 1; }
  }
</style>
