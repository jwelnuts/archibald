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
