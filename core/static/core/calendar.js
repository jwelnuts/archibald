const initCalendar = () => {
  const calendarEl = document.getElementById("dashboard-calendar");
  const Calendar = window.tui && window.tui.Calendar ? window.tui.Calendar : null;
  if (!calendarEl || !Calendar) return false;

  let eventsByDate = {};
  const monthLabelEl = document.getElementById("calendar-month-label");
  const detailDateEl = document.getElementById("calendar-detail-date");
  const detailListEl = document.getElementById("calendar-detail-list");
  const monthListEl = document.getElementById("calendar-month-list");

  const normalizeDate = (value) => {
    if (!value) return new Date();
    if (value instanceof Date) return value;
    if (typeof value.getTime === "function") return new Date(value.getTime());
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? new Date() : parsed;
  };

  const formatMonth = (dateObj) =>
    normalizeDate(dateObj).toLocaleDateString("it-IT", { month: "long", year: "numeric" });
  const formatDay = (dateObj) =>
    normalizeDate(dateObj).toLocaleDateString("it-IT", {
      weekday: "long",
      day: "2-digit",
      month: "long",
    });

  const renderDayDetails = (dateObj) => {
    if (!detailListEl || !detailDateEl) return;
    const key = normalizeDate(dateObj).toISOString().slice(0, 10);
    const items = eventsByDate[key] || [];
    detailDateEl.textContent = formatDay(dateObj);
    detailListEl.innerHTML = "";
    if (!items.length) {
      const empty = document.createElement("div");
      empty.className = "calendar-empty";
      empty.textContent = "Nessun evento per questa data.";
      detailListEl.appendChild(empty);
      return;
    }
    items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "calendar-event-row";
      const chip = document.createElement("span");
      chip.className = `event-chip event-${item.kind}`;
      chip.textContent = item.label;
      const count = document.createElement("span");
      count.className = "calendar-event-count";
      count.textContent = item.count ? String(item.count) : "";
      row.appendChild(chip);
      row.appendChild(count);
      detailListEl.appendChild(row);
    });
  };

  const renderMonthSummary = () => {
    if (!monthListEl) return;
    const summary = {};
    Object.values(eventsByDate).forEach((items) => {
      items.forEach((item) => {
        summary[item.kind] = (summary[item.kind] || 0) + (item.count || 1);
      });
    });
    monthListEl.innerHTML = "";
    const kinds = [
      { key: "task", label: "Task" },
      { key: "planner", label: "Planner" },
      { key: "subscription", label: "Abbonamenti" },
      { key: "transaction", label: "Transazioni" },
      { key: "routine", label: "Routine" },
    ];
    const hasAny = kinds.some((k) => summary[k.key]);
    if (!hasAny) {
      const empty = document.createElement("div");
      empty.className = "calendar-empty";
      empty.textContent = "Nessun evento nel mese selezionato.";
      monthListEl.appendChild(empty);
      return;
    }
    kinds.forEach((kind) => {
      const count = summary[kind.key] || 0;
      if (!count) return;
      const row = document.createElement("div");
      row.className = "calendar-event-row";
      const chip = document.createElement("span");
      chip.className = `event-chip event-${kind.key}`;
      chip.textContent = kind.label;
      const countEl = document.createElement("span");
      countEl.className = "calendar-event-count";
      countEl.textContent = String(count);
      row.appendChild(chip);
      row.appendChild(countEl);
      monthListEl.appendChild(row);
    });
  };

  const calendar = new Calendar(calendarEl, {
    defaultView: "month",
    usageStatistics: false,
    isReadOnly: true,
    week: {
      startDayOfWeek: 1,
      dayNames: ["Dom", "Lun", "Mar", "Mer", "Gio", "Ven", "Sab"],
    },
    month: {
      startDayOfWeek: 1,
      dayNames: ["Dom", "Lun", "Mar", "Mer", "Gio", "Ven", "Sab"],
    },
    calendars: [
      { id: "task", name: "Task", backgroundColor: "#1971c2", borderColor: "#1971c2" },
      { id: "planner", name: "Planner", backgroundColor: "#2f9e44", borderColor: "#2f9e44" },
      { id: "subscription", name: "Abbonamenti", backgroundColor: "#f08c00", borderColor: "#f08c00" },
      { id: "transaction", name: "Transazioni", backgroundColor: "#7048e8", borderColor: "#7048e8" },
      { id: "routine", name: "Routine", backgroundColor: "#0f766e", borderColor: "#0f766e" },
    ],
  });

  const syncMonthLabel = () => {
    if (!monthLabelEl) return;
    const current = normalizeDate(calendar.getDate());
    monthLabelEl.textContent = formatMonth(current);
  };

  const currentRange = () => {
    const d = normalizeDate(calendar.getDate());
    const start = new Date(d.getFullYear(), d.getMonth(), 1);
    const end = new Date(d.getFullYear(), d.getMonth() + 1, 0);
    return { start, end };
  };

  const loadEvents = (start, end) => {
    const startIso = start.toISOString().slice(0, 10);
    const endIso = end.toISOString().slice(0, 10);
    fetch(`/calendar/events?start=${startIso}&end=${endIso}`, { credentials: "same-origin" })
      .then((resp) => (resp.ok ? resp.json() : null))
      .then((data) => {
        eventsByDate = {};
        if (data && Array.isArray(data.events)) {
          data.events.forEach((evt) => {
            eventsByDate[evt.date] = evt.items || [];
          });
        }
        renderMonthSummary();
        calendar.clear();
        const calEvents = [];
        Object.entries(eventsByDate).forEach(([date, items]) => {
          items.forEach((item, idx) => {
            calEvents.push({
              id: `${date}-${item.kind}-${idx}`,
              calendarId: item.kind,
              title: item.count ? `${item.label} · ${item.count}` : item.label,
              category: "allday",
              start: date,
              end: date,
              raw: item,
            });
          });
        });
        if (calEvents.length) {
          calendar.createEvents(calEvents);
        }
      })
      .catch(() => {
        eventsByDate = {};
        renderMonthSummary();
        calendar.clear();
      });
  };

  let lastMonthKey = "";
  const range = currentRange();
  lastMonthKey = `${range.start.getFullYear()}-${range.start.getMonth()}`;
  syncMonthLabel();
  loadEvents(range.start, range.end);
    renderDayDetails(new Date());

  const prevBtn = document.getElementById("calendar-prev");
  const nextBtn = document.getElementById("calendar-next");
  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      calendar.prev();
    });
  }
  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      calendar.next();
    });
  }

  calendar.on("clickDayname", (event) => {
    renderDayDetails(event.date);
  });

  calendar.on("selectDateTime", (event) => {
    if (event && event.start) {
      renderDayDetails(event.start);
    }
  });

  calendar.on("clickEvent", (event) => {
    renderDayDetails(event.event.start);
  });

  calendar.on("afterRender", () => {
    const newRange = currentRange();
    const newKey = `${newRange.start.getFullYear()}-${newRange.start.getMonth()}`;
    if (newKey !== lastMonthKey) {
      lastMonthKey = newKey;
      syncMonthLabel();
      loadEvents(newRange.start, newRange.end);
    } else {
      syncMonthLabel();
    }
  });

  return true;
};

const bootCalendar = () => {
  const calendarEl = document.getElementById("dashboard-calendar");
  if (!calendarEl) return;
  if (!(window.tui && window.tui.Calendar)) {
    calendarEl.innerHTML = '<div class="calendar-empty">Calendario non caricato.</div>';
    return;
  }
  if (!initCalendar()) {
    calendarEl.innerHTML = '<div class="calendar-empty">Calendario non caricato.</div>';
  }
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootCalendar);
} else {
  bootCalendar();
}
