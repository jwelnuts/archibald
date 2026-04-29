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
