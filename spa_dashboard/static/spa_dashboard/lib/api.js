const CSRF = window.__CSRF__

export async function fetchLayout() {
  const res = await fetch('/api/spa/layout')
  if (!res.ok) throw new Error(`fetchLayout failed: ${res.status}`)
  return res.json()
}

export async function saveLayout(layout) {
  const res = await fetch('/api/spa/layout/save', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': CSRF,
    },
    body: JSON.stringify({ layout }),
  })
  if (!res.ok) throw new Error(`saveLayout failed: ${res.status}`)
  return res.json()
}

export async function fetchWidgetData(widgetId) {
  const res = await fetch(`/api/spa/widget/${widgetId}/data`)
  if (!res.ok) throw new Error(`fetchWidgetData failed: ${res.status}`)
  return res.json()
}
