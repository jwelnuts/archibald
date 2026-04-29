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
