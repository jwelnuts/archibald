<script>
  let { slot, data } = $props()

  let total = $derived(data.total ?? 0)
  let projects = $derived(data.projects ?? [])
</script>

<div class="proj-widget">
  <div class="proj-header">
    <div class="proj-title">
      <span class="proj-icon">◆</span>
      Progetti
    </div>
    <a href="/projects/" class="proj-link" title="Vai ai progetti">↗</a>
  </div>

  <div class="proj-kpi-row">
    <div class="proj-kpi">
      <span class="proj-kpi-value">{total}</span>
      <span class="proj-kpi-label">{total === 1 ? 'progetto attivo' : 'progetti attivi'}</span>
    </div>
  </div>

  {#if projects.length > 0}
    <ul class="proj-list">
      {#each projects as project}
        <li class="proj-row">
          <div class="proj-row-top">
            <a class="proj-name" href={project.url}>{project.name}</a>
            {#if project.next_due}
              <span class="proj-due">scad. {project.next_due}</span>
            {/if}
          </div>
          {#if project.counts.total > 0}
            <div class="proj-pills">
              {#if project.counts.in_progress > 0}
                <span class="proj-pill pill-progress">{project.counts.in_progress} in corso</span>
              {/if}
              {#if project.counts.blocked > 0}
                <span class="proj-pill pill-blocked">{project.counts.blocked} bloccati</span>
              {/if}
              {#if project.counts.planned > 0}
                <span class="proj-pill pill-planned">{project.counts.planned} pianificati</span>
              {/if}
              <span class="proj-pill pill-done">{project.counts.done}/{project.counts.total} completati</span>
            </div>
          {:else}
            <span class="proj-no-subs">Nessun sotto-progetto</span>
          {/if}
        </li>
      {/each}
    </ul>
  {:else}
    <div class="proj-empty">Nessun progetto attivo</div>
  {/if}
</div>

<style>
  .proj-widget {
    background: #fff;
    border-radius: 10px;
    border: 1px solid #e8e2db;
    padding: 1rem;
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    box-sizing: border-box;
  }

  .proj-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .proj-title {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #78716c;
  }

  .proj-icon { color: #f59e0b; font-size: 0.7rem; }

  .proj-link {
    font-size: 0.85rem;
    color: #a8a29e;
    text-decoration: none;
    transition: color 0.15s;
  }
  .proj-link:hover { color: #f59e0b; }

  .proj-kpi-row {
    display: flex;
    align-items: center;
  }

  .proj-kpi { display: flex; flex-direction: column; gap: 2px; }

  .proj-kpi-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #1c1917;
    line-height: 1;
  }

  .proj-kpi-label { font-size: 0.72rem; color: #a8a29e; }

  .proj-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow: hidden;
  }

  .proj-row {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    padding: 0.4rem 0;
    border-bottom: 1px solid #f5f0eb;
  }
  .proj-row:last-child { border-bottom: none; }

  .proj-row-top {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.5rem;
  }

  .proj-name {
    font-size: 0.82rem;
    font-weight: 600;
    color: #1c1917;
    text-decoration: none;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex: 1;
  }
  .proj-name:hover { color: #f59e0b; }

  .proj-due {
    font-size: 0.7rem;
    color: #a8a29e;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .proj-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
  }

  .proj-pill {
    font-size: 0.68rem;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 99px;
    white-space: nowrap;
  }

  .pill-progress { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
  .pill-blocked  { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
  .pill-planned  { background: #f5f5f4; color: #78716c; border: 1px solid #d6d3d1; }
  .pill-done     { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }

  .proj-no-subs {
    font-size: 0.72rem;
    color: #d6d3d1;
  }

  .proj-empty {
    font-size: 0.8rem;
    color: #a8a29e;
    text-align: center;
    padding: 1rem 0;
  }
</style>
