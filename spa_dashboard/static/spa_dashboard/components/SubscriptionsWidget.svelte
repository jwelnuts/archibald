<script>
  import { widgetData } from '../lib/store.svelte.js'

  let { slot, data } = $props()

  let counts = $derived(data.counts ?? { active: 0, paused: 0, canceled: 0 })
  let upcoming = $derived(data.upcoming ?? [])
  let totalDue = $derived(data.total_due ?? '0.00')
  let nextDueDate = $derived(data.next_due_date ?? null)
  let accounts = $derived(data.accounts ?? [])

  // pay state: null | { item }
  let paying = $state(null)
  let selectedAccount = $state('')
  let payStatus = $state('idle') // idle | loading | ok | error
  let payMessage = $state('')

  function openPay(item) {
    paying = item
    selectedAccount = accounts.length === 1 ? String(accounts[0].id) : ''
    payStatus = 'idle'
    payMessage = ''
  }

  function closePay() {
    paying = null
    selectedAccount = ''
    payStatus = 'idle'
    payMessage = ''
  }

  async function confirmPay() {
    if (!selectedAccount) return
    payStatus = 'loading'

    const body = {
      account_id: Number(selectedAccount),
      due_date: paying.due_date_raw,
    }
    if (paying.occurrence_id) {
      body.occurrence_id = paying.occurrence_id
    } else {
      body.subscription_id = paying.subscription_id
    }

    try {
      const res = await fetch('/api/spa/subscriptions/pay', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': window.__CSRF__ ?? '',
        },
        body: JSON.stringify(body),
      })
      const json = await res.json()
      if (json.ok) {
        payStatus = 'ok'
        payMessage = json.message ?? 'Pagamento registrato.'
        // refresh widget data after short delay
        setTimeout(async () => {
          closePay()
          const r = await fetch(`/api/spa/widget/${slot.id}/data`)
          const d = await r.json()
          widgetData[slot.id] = d.data
        }, 800)
      } else {
        payStatus = 'error'
        payMessage = json.error ?? 'Errore.'
      }
    } catch {
      payStatus = 'error'
      payMessage = 'Errore di rete.'
    }
  }
</script>

<div class="subs-widget">
  <div class="subs-header">
    <div class="subs-title">
      <span class="subs-icon">◈</span>
      Abbonamenti
    </div>
    <a href="/subs/" class="subs-link" title="Gestisci abbonamenti">↗</a>
  </div>

  <div class="subs-kpi-row">
    <div class="subs-kpi">
      <span class="subs-kpi-value">€{totalDue}</span>
      {#if nextDueDate}
        <span class="subs-kpi-label">prossima il {nextDueDate}</span>
      {:else}
        <span class="subs-kpi-label">nessuna scadenza</span>
      {/if}
    </div>
    <div class="subs-pills">
      <span class="pill pill-active">{counts.active} attivi</span>
      {#if counts.paused > 0}
        <span class="pill pill-paused">{counts.paused} in pausa</span>
      {/if}
    </div>
  </div>

  {#if upcoming.length > 0}
    <ul class="subs-list">
      {#each upcoming as item}
        <li class="subs-row" class:is-paying={paying === item}>
          <span class="subs-date">{item.date}</span>
          <span class="subs-name">{item.name}</span>
          <span class="subs-amount">{item.amount} {item.currency}</span>
          {#if paying !== item}
            <button class="btn-pay" onclick={() => openPay(item)}>Pagato</button>
          {:else}
            <button class="btn-cancel" onclick={closePay}>✕</button>
          {/if}

          {#if paying === item}
            <div class="pay-inline">
              {#if accounts.length === 0}
                <span class="pay-msg-warn">Nessun conto disponibile.</span>
              {:else}
                <select class="pay-select" bind:value={selectedAccount} disabled={payStatus === 'loading'}>
                  {#if accounts.length > 1}
                    <option value="">Seleziona conto…</option>
                  {/if}
                  {#each accounts as acc}
                    <option value={String(acc.id)}>{acc.name} ({acc.currency})</option>
                  {/each}
                </select>
                <button
                  class="btn-confirm"
                  onclick={confirmPay}
                  disabled={!selectedAccount || payStatus === 'loading'}
                >
                  {#if payStatus === 'loading'}…{:else}Conferma{/if}
                </button>
              {/if}
              {#if payStatus === 'ok'}
                <span class="pay-msg-ok">{payMessage}</span>
              {:else if payStatus === 'error'}
                <span class="pay-msg-err">{payMessage}</span>
              {/if}
            </div>
          {/if}
        </li>
      {/each}
    </ul>
  {:else}
    <div class="subs-empty">Nessuna scadenza imminente</div>
  {/if}
</div>

<style>
  .subs-widget {
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

  .subs-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .subs-title {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #78716c;
  }

  .subs-icon { color: #f59e0b; font-size: 0.75rem; }

  .subs-link {
    font-size: 0.85rem;
    color: #a8a29e;
    text-decoration: none;
    transition: color 0.15s;
  }
  .subs-link:hover { color: #f59e0b; }

  .subs-kpi-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .subs-kpi { display: flex; flex-direction: column; gap: 2px; }

  .subs-kpi-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #1c1917;
    line-height: 1;
  }

  .subs-kpi-label { font-size: 0.72rem; color: #a8a29e; }

  .subs-pills { display: flex; flex-wrap: wrap; gap: 0.3rem; align-items: flex-start; }

  .pill {
    font-size: 0.7rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 99px;
    white-space: nowrap;
  }
  .pill-active  { background: #ecfdf5; color: #166534; border: 1px solid #bbf7d0; }
  .pill-paused  { background: #fffbeb; color: #92400e; border: 1px solid #fde68a; }

  .subs-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow: hidden;
  }

  .subs-row {
    display: grid;
    grid-template-columns: 5.5rem 1fr auto auto;
    align-items: center;
    gap: 0.4rem;
    padding: 0.35rem 0;
    border-bottom: 1px solid #f5f0eb;
    font-size: 0.8rem;
    transition: background 0.15s;
  }
  .subs-row:last-child { border-bottom: none; }
  .subs-row.is-paying { flex-wrap: wrap; display: flex; flex-direction: column; align-items: stretch; }

  .subs-date  { color: #a8a29e; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .subs-name  { color: #1c1917; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .subs-amount { color: #1c1917; font-weight: 600; font-variant-numeric: tabular-nums; white-space: nowrap; text-align: right; }

  .btn-pay {
    font-size: 0.7rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 6px;
    border: 1px solid #d6c9b8;
    background: #faf7f4;
    color: #78716c;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.12s, color 0.12s;
  }
  .btn-pay:hover { background: #f59e0b; color: #fff; border-color: #f59e0b; }

  .btn-cancel {
    font-size: 0.75rem;
    padding: 2px 6px;
    border-radius: 6px;
    border: 1px solid #e8e2db;
    background: transparent;
    color: #a8a29e;
    cursor: pointer;
  }

  .pay-inline {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.4rem 0 0.2rem;
    flex-wrap: wrap;
  }

  .pay-select {
    flex: 1;
    min-width: 0;
    font-size: 0.78rem;
    padding: 3px 6px;
    border: 1px solid #d6c9b8;
    border-radius: 6px;
    background: #faf7f4;
    color: #1c1917;
  }

  .btn-confirm {
    font-size: 0.75rem;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 6px;
    border: none;
    background: #f59e0b;
    color: #fff;
    cursor: pointer;
    white-space: nowrap;
  }
  .btn-confirm:disabled { opacity: 0.5; cursor: default; }

  .pay-msg-ok   { font-size: 0.72rem; color: #166534; }
  .pay-msg-err  { font-size: 0.72rem; color: #c0392b; }
  .pay-msg-warn { font-size: 0.72rem; color: #92400e; }

  .subs-empty {
    font-size: 0.8rem;
    color: #a8a29e;
    text-align: center;
    padding: 1rem 0;
  }
</style>
