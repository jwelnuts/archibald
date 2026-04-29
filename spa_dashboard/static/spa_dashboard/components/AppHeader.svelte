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
