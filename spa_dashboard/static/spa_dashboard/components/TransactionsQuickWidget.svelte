<script>
  import { widgetData } from '../lib/store.svelte.js'

  let { slot, data } = $props()

  let accounts = $derived(data.accounts ?? [])
  let projects = $derived(data.projects ?? [])
  let categories = $derived(data.categories ?? [])
  let currencies = $derived(data.currencies ?? [])
  let txTypes = $derived(data.tx_types ?? [])
  let recentCount = $derived(data.recent_count ?? 0)

  let amount = $state('')
  let txType = $state('OUT')
  let accountId = $state('')
  let projectId = $state('')
  let categoryId = $state('')
  let currencyId = $state('')
  let note = $state('')
  let date = $state(data.today ?? '')

  let status = $state('idle') // idle | loading | ok | error
  let statusMessage = $state('')

  $effect(() => {
    if (accounts.length === 1) accountId = String(accounts[0].id)
    if (currencies.length === 1) currencyId = String(currencies[0].id)
  })

  const presets = [5, 10, 20, 50, 100, 200]

  function setPreset(value) {
    amount = String(value)
  }

  async function submit(e) {
    e?.preventDefault()
    if (!amount || !accountId) return

    status = 'loading'
    statusMessage = ''

    try {
      const res = await fetch('/api/spa/transactions/quick', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': window.__CSRF__ ?? '',
        },
        body: JSON.stringify({
          amount: parseFloat(amount),
          tx_type: txType,
          account_id: Number(accountId),
          project_id: projectId ? Number(projectId) : null,
          category_id: categoryId ? Number(categoryId) : null,
          currency_id: currencyId ? Number(currencyId) : null,
          note: note.trim() || null,
          date: date || null,
        }),
      })
      const json = await res.json()
      if (json.ok) {
        status = 'ok'
        statusMessage = json.message
        amount = ''
        note = ''
        recentCount += 1
        setTimeout(async () => {
          status = 'idle'
          const r = await fetch(`/api/spa/widget/${slot.id}/data`)
          const d = await r.json()
          widgetData[slot.id] = d.data
        }, 1200)
      } else {
        status = 'error'
        statusMessage = json.error ?? 'Errore.'
        setTimeout(() => { status = 'idle' }, 2000)
      }
    } catch {
      status = 'error'
      statusMessage = 'Errore di rete.'
      setTimeout(() => { status = 'idle' }, 2000)
    }
  }
</script>

<div class="tx-quick-widget">
  <div class="txq-header">
    <div class="txq-title">
      <span class="txq-icon">⚡</span>
      Transazione rapida
    </div>
    <a href="/transactions/" class="txq-link" title="Vai al registro">↗</a>
  </div>

  <div class="txq-kpi-row">
    <div class="txq-kpi">
      <span class="txq-kpi-value">{recentCount}</span>
      <span class="txq-kpi-label">ultimi 7 giorni</span>
    </div>
  </div>

  <form class="txq-form" onsubmit={submit}>
    <div class="txq-type-row">
      {#each txTypes as t}
        <button
          type="button"
          class="txq-type-btn"
          class:active={txType === t.value}
          class:is-out={t.value === 'OUT'}
          class:is-in={t.value === 'IN'}
          class:is-xfer={t.value === 'XFER'}
          onclick={() => txType = t.value}
        >{t.label}</button>
      {/each}
    </div>

    <div class="txq-presets">
      {#each presets as p}
        <button type="button" class="txq-preset" class:active={amount === String(p)} onclick={() => setPreset(p)}>{p}</button>
      {/each}
    </div>

    <div class="txq-fields">
      <div class="txq-amount-row">
        <input
          class="txq-amount"
          type="number"
          step="0.01"
          min="0"
          placeholder="0.00"
          bind:value={amount}
          required
        >
        {#if currencies.length > 1}
          <select class="txq-currency" bind:value={currencyId}>
            {#each currencies as c}
              <option value={String(c.id)}>{c.code}</option>
            {/each}
          </select>
        {:else if currencies.length === 1}
          <span class="txq-currency-fixed">{currencies[0].code}</span>
        {/if}
      </div>

      <select class="txq-select" bind:value={accountId}>
        <option value="">Conto...</option>
        {#each accounts as acc}
          <option value={String(acc.id)}>{acc.name} ({acc.currency})</option>
        {/each}
      </select>

      <select class="txq-select" bind:value={projectId}>
        <option value="">Progetto (opzionale)</option>
        {#each projects as p}
          <option value={String(p.id)}>{p.name}</option>
        {/each}
      </select>

      <select class="txq-select" bind:value={categoryId}>
        <option value="">Categoria (opzionale)</option>
        {#each categories as c}
          <option value={String(c.id)}>{c.name}</option>
        {/each}
      </select>

      <input
        class="txq-input"
        type="date"
        bind:value={date}
      >

      <input
        class="txq-input"
        type="text"
        placeholder="Nota (opzionale)"
        bind:value={note}
      >
    </div>

    <button class="txq-submit" type="submit" disabled={!amount || !accountId || status === 'loading'}>
      {#if status === 'loading'}
        Salvo...
      {:else if status === 'ok'}
        ✓ {statusMessage}
      {:else if status === 'error'}
        ✕ {statusMessage}
      {:else}
        Registra {txType === 'OUT' ? 'uscita' : txType === 'IN' ? 'entrata' : 'trasferimento'}
      {/if}
    </button>
  </form>
</div>

<style>
  .tx-quick-widget {
    background: #fff;
    border-radius: 10px;
    border: 1px solid #e8e2db;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    box-sizing: border-box;
  }

  .txq-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .txq-title {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #78716c;
  }

  .txq-icon { font-size: 0.8rem; }

  .txq-link {
    font-size: 0.85rem;
    color: #a8a29e;
    text-decoration: none;
    transition: color 0.15s;
  }
  .txq-link:hover { color: #667eea; }

  .txq-kpi-row {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .txq-kpi { display: flex; flex-direction: column; gap: 2px; }

  .txq-kpi-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #1c1917;
    line-height: 1;
  }

  .txq-kpi-label { font-size: 0.72rem; color: #a8a29e; }

  .txq-type-row {
    display: flex;
    gap: 0;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #e8e2db;
  }

  .txq-type-btn {
    flex: 1;
    padding: 6px 0;
    border: none;
    border-right: 1px solid #e8e2db;
    background: #faf7f4;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    color: #78716c;
    transition: background 0.15s, color 0.15s;
    text-align: center;
  }
  .txq-type-btn:last-child { border-right: none; }
  .txq-type-btn.active.is-out  { background: #ef4444; color: #fff; }
  .txq-type-btn.active.is-in   { background: #22c55e; color: #fff; }
  .txq-type-btn.active.is-xfer { background: #3b82f6; color: #fff; }

  .txq-presets {
    display: flex;
    gap: 0.3rem;
    flex-wrap: wrap;
  }

  .txq-preset {
    font-size: 0.72rem;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 6px;
    border: 1px solid #e8e2db;
    background: #faf7f4;
    color: #78716c;
    cursor: pointer;
    transition: all 0.12s;
  }
  .txq-preset:hover { border-color: #667eea; color: #667eea; }
  .txq-preset.active { background: #667eea; color: #fff; border-color: #667eea; }

  .txq-fields {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .txq-amount-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .txq-amount {
    flex: 1;
    font-size: 1.1rem;
    font-weight: 700;
    padding: 6px 10px;
    border: 1px solid #e8e2db;
    border-radius: 8px;
    background: #faf7f4;
    color: #1c1917;
    width: 100%;
    font-variant-numeric: tabular-nums;
  }
  .txq-amount:focus { outline: none; border-color: #667eea; }

  .txq-currency-fixed {
    font-size: 0.85rem;
    font-weight: 600;
    color: #78716c;
    padding: 0 4px;
  }

  .txq-currency, .txq-select, .txq-input {
    font-size: 0.78rem;
    padding: 5px 8px;
    border: 1px solid #e8e2db;
    border-radius: 8px;
    background: #faf7f4;
    color: #1c1917;
    width: 100%;
  }
  .txq-currency:focus, .txq-select:focus, .txq-input:focus { outline: none; border-color: #667eea; }

  .txq-submit {
    width: 100%;
    padding: 8px;
    border: none;
    border-radius: 8px;
    background: #667eea;
    color: #fff;
    font-size: 0.82rem;
    font-weight: 700;
    cursor: pointer;
    transition: background 0.15s;
    text-align: center;
  }
  .txq-submit:hover { background: #5a6fd6; }
  .txq-submit:disabled { opacity: 0.5; cursor: default; }
</style>
