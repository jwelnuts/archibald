import htmx from "htmx.org";
import { startStimulus } from "./stimulus.js";
import { initPayeePicker } from "./payee_picker.js";

window.htmx = htmx;
startStimulus().catch(() => {});
initPayeePicker();

const getCsrfToken = () => {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
};

const portal = document.getElementById("portal");
const dashboardWidgetsRoot = document.querySelector("[data-dashboard-widgets]");

const setupDashboardWidgets = () => {
  if (!portal || !dashboardWidgetsRoot) return;

  const saveUrl = dashboardWidgetsRoot.getAttribute("data-save-url") || "";
  const filterWrap = document.querySelector("[data-portal-filter]");
  const chips = filterWrap ? filterWrap.querySelectorAll(".filter-chip") : [];
  const editToggle = dashboardWidgetsRoot.querySelector("[data-widget-edit-toggle]");
  const resetButton = dashboardWidgetsRoot.querySelector("[data-widget-reset]");
  const statusLabel = dashboardWidgetsRoot.querySelector("[data-widget-status]");
  const hiddenPanel = dashboardWidgetsRoot.querySelector("[data-widget-hidden-panel]");
  const hiddenList = dashboardWidgetsRoot.querySelector("[data-widget-hidden-list]");

  let dragging = null;
  let activeFilter = "all";
  let editMode = false;
  let saveTimer = null;

  const cards = () => Array.from(portal.querySelectorAll("[data-widget-card]"));
  const initialOrder = cards().map((card) => card.getAttribute("data-widget-id"));

  const getDragAfterElement = (container, y) => {
    const elements = [...container.querySelectorAll(".portlet:not(.is-dragging):not(.is-hidden)")];
    return elements.reduce(
      (closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {
          return { offset, element: child };
        }
        return closest;
      },
      { offset: Number.NEGATIVE_INFINITY, element: null }
    ).element;
  };

  const refreshStatus = () => {
    if (!statusLabel) return;
    const hiddenCount = cards().filter((card) => card.classList.contains("is-user-hidden")).length;
    statusLabel.textContent = editMode
      ? `Personalizzazione attiva · ${hiddenCount} nascosti`
      : "Lista moduli operativi";
  };

  const refreshHiddenPanel = () => {
    if (!hiddenPanel || !hiddenList) return;
    const hiddenCards = cards().filter((card) => card.classList.contains("is-user-hidden"));
    hiddenList.innerHTML = "";
    if (!hiddenCards.length) {
      hiddenPanel.hidden = true;
      return;
    }
    hiddenPanel.hidden = false;
    hiddenCards.forEach((card) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "widget-restore-btn";
      button.setAttribute("data-widget-restore", card.getAttribute("data-widget-id") || "");
      const title = card.querySelector(".portlet-title");
      button.textContent = title ? `Ripristina ${title.textContent.trim()}` : "Ripristina widget";
      hiddenList.appendChild(button);
    });
  };

  const refreshVisibility = () => {
    cards().forEach((card) => {
      const group = card.getAttribute("data-group");
      const filtered = activeFilter !== "all" && group !== activeFilter;
      card.classList.toggle("is-filter-hidden", filtered);
      const isHidden = card.classList.contains("is-user-hidden") || filtered;
      card.classList.toggle("is-hidden", isHidden);
      card.setAttribute("draggable", editMode && !isHidden ? "true" : "false");
    });
    refreshHiddenPanel();
    refreshStatus();
  };

  const persistWidgets = async () => {
    if (!saveUrl) return;
    const payload = {
      order: cards().map((card) => card.getAttribute("data-widget-id")).filter(Boolean),
      hidden: cards()
        .filter((card) => card.classList.contains("is-user-hidden"))
        .map((card) => card.getAttribute("data-widget-id"))
        .filter(Boolean),
    };

    try {
      await fetch(saveUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify(payload),
      });
    } catch (_err) {
      // ignore: UI resta utilizzabile anche offline/errore rete.
    }
  };

  const queuePersist = () => {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = window.setTimeout(persistWidgets, 220);
  };

  const setFilter = (filter) => {
    activeFilter = filter;
    chips.forEach((chip) => {
      chip.classList.toggle("active", (chip.getAttribute("data-filter") || "all") === filter);
    });
    refreshVisibility();
  };

  const restoreWidget = (widgetId) => {
    const target = cards().find((card) => card.getAttribute("data-widget-id") === widgetId);
    if (!target) return;
    target.classList.remove("is-user-hidden");
    refreshVisibility();
    queuePersist();
  };

  const moveWidget = (card, direction) => {
    if (!card) return;
    if (direction === "up") {
      const prev = card.previousElementSibling;
      if (prev) {
        portal.insertBefore(card, prev);
      }
    } else if (direction === "down") {
      const next = card.nextElementSibling;
      if (next) {
        portal.insertBefore(next, card);
      }
    }
    refreshVisibility();
    queuePersist();
  };

  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      setFilter(chip.getAttribute("data-filter") || "all");
    });
  });

  if (editToggle) {
    editToggle.addEventListener("click", () => {
      editMode = !editMode;
      dashboardWidgetsRoot.classList.toggle("is-editing", editMode);
      editToggle.textContent = editMode ? "Fine personalizzazione" : "Personalizza";
      refreshVisibility();
    });
  }

  if (resetButton) {
    resetButton.addEventListener("click", () => {
      initialOrder.forEach((widgetId) => {
        const card = cards().find((row) => row.getAttribute("data-widget-id") === widgetId);
        if (card) {
          portal.appendChild(card);
        }
      });
      cards().forEach((card) => card.classList.remove("is-user-hidden", "is-filter-hidden"));
      setFilter("all");
      queuePersist();
    });
  }

  if (hiddenList) {
    hiddenList.addEventListener("click", (event) => {
      const btn = event.target.closest("[data-widget-restore]");
      if (!btn) return;
      restoreWidget(btn.getAttribute("data-widget-restore") || "");
    });
  }

  portal.addEventListener("click", (event) => {
    const moveButton = event.target.closest("[data-widget-move]");
    if (moveButton && editMode) {
      const card = moveButton.closest("[data-widget-card]");
      moveWidget(card, moveButton.getAttribute("data-widget-move"));
      return;
    }

    const hideButton = event.target.closest("[data-widget-hide]");
    if (!hideButton || !editMode) return;
    const card = hideButton.closest("[data-widget-card]");
    if (!card) return;
    card.classList.add("is-user-hidden");
    refreshVisibility();
    queuePersist();
  });

  portal.addEventListener("dragstart", (event) => {
    if (!editMode) return;
    const card = event.target.closest("[data-widget-card]");
    if (!card || card.classList.contains("is-hidden")) return;
    dragging = card;
    card.classList.add("is-dragging");
    portal.classList.add("is-dragging");
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", "");
    }
  });

  portal.addEventListener("dragend", (event) => {
    const card = event.target.closest("[data-widget-card]");
    if (!card) return;
    card.classList.remove("is-dragging");
    portal.classList.remove("is-dragging");
    if (dragging) {
      queuePersist();
    }
    dragging = null;
  });

  portal.addEventListener("dragover", (event) => {
    if (!dragging || !editMode) return;
    event.preventDefault();
    const after = getDragAfterElement(portal, event.clientY);
    if (!after) {
      portal.appendChild(dragging);
    } else if (after !== dragging) {
      portal.insertBefore(dragging, after);
    }
  });

  setFilter("all");
};

setupDashboardWidgets();

const configEl = document.getElementById("hero-actions-config");
if (configEl) {
  try {
    window.HERO_ACTIONS_CONFIG = JSON.parse(configEl.textContent);
  } catch (err) {
    window.HERO_ACTIONS_CONFIG = {};
  }
}

const overrideEl = document.getElementById("hero-actions-override");
if (overrideEl) {
  try {
    window.HERO_ACTIONS_OVERRIDE = JSON.parse(overrideEl.textContent);
  } catch (err) {
    window.HERO_ACTIONS_OVERRIDE = {};
  }
}

document.querySelectorAll(".hero-actions[data-module]").forEach((container) => {
  const module = container.getAttribute("data-module");
  const overrideRoot = window.HERO_ACTIONS_OVERRIDE || {};
  if (overrideRoot && overrideRoot._configured && Array.isArray(overrideRoot[module])) {
    const config = overrideRoot[module];
    container.querySelectorAll("[data-action]").forEach((action) => {
      const key = action.getAttribute("data-action");
      if (!config.includes(key)) {
        action.style.display = "none";
      }
    });
    return;
  }

  const configRoot = window.HERO_ACTIONS_CONFIG || {};
  if (!configRoot._configured) return;
  const config = Array.isArray(configRoot[module]) ? configRoot[module] : [];
  container.querySelectorAll("[data-action]").forEach((action) => {
    const key = action.getAttribute("data-action");
    if (!config.includes(key)) {
      action.style.display = "none";
    }
  });
});

const dashForm = document.getElementById("dashboard-archibald-form");
const dashChat = document.getElementById("dashboard-archibald-chat");
const dashPrompt = document.getElementById("dashboard-archibald-prompt");
const dashThread = document.getElementById("dashboard-archibald-thread");
const dashReset = document.getElementById("dashboard-archibald-reset");
const dashStatus = document.getElementById("dashboard-archibald-status");
const dashFloating = document.getElementById("dashboard-archibald-floating");
const dashLauncher = document.getElementById("dashboard-archibald-launch");
const dashClose = document.getElementById("dashboard-archibald-close");

if (dashForm && dashChat && dashPrompt && dashThread) {
  const setStatus = (text) => {
    if (!dashStatus) return;
    dashStatus.textContent = text;
  };

  const showChatPanel = () => {
    if (!dashFloating) return;
    dashFloating.classList.remove("uk-hidden");
    dashPrompt.focus();
  };

  const hideChatPanel = () => {
    if (!dashFloating) return;
    dashFloating.classList.add("uk-hidden");
  };

  const addMessage = (role, content, time, pending = false) => {
    const wrapper = document.createElement("div");
    wrapper.className = `chat-message ${role}${pending ? " is-pending" : ""}`;
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble";
    const roleEl = document.createElement("div");
    roleEl.className = "chat-role";
    roleEl.textContent = role === "user" ? "Tu" : "Archibald";
    const text = document.createElement("div");
    text.className = "chat-text";
    text.textContent = content;
    const meta = document.createElement("div");
    meta.className = "chat-meta";
    const timeEl = document.createElement("span");
    timeEl.className = "chat-time";
    timeEl.textContent = time || "";
    meta.appendChild(timeEl);
    bubble.appendChild(roleEl);
    bubble.appendChild(text);
    bubble.appendChild(meta);
    wrapper.appendChild(bubble);
    dashChat.appendChild(wrapper);
    dashChat.scrollTop = dashChat.scrollHeight;
    return wrapper;
  };

  if (dashLauncher) {
    dashLauncher.addEventListener("click", (event) => {
      event.preventDefault();
      showChatPanel();
    });
  }

  if (dashClose) {
    dashClose.addEventListener("click", (event) => {
      event.preventDefault();
      hideChatPanel();
    });
  }

  dashForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = dashPrompt.value.trim();
    if (!text) return;
    showChatPanel();
    addMessage("user", text);
    dashPrompt.value = "";
    setStatus("Archibald sta scrivendo...");
    const pendingNode = addMessage("assistant", "...", "", true);
    const data = new FormData();
    data.append("prompt", text);
    if (dashThread.value) {
      data.append("thread_id", dashThread.value);
    }
    try {
      const resp = await fetch("/archibald/quick", {
        method: "POST",
        body: data,
        headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": getCsrfToken() },
        credentials: "same-origin",
      });
      if (!resp.ok) {
        pendingNode.remove();
        addMessage("assistant", "C'e stato un problema di connessione. Riprova tra poco.");
        setStatus("Offline");
        return;
      }
      const payload = await resp.json();
      pendingNode.remove();
      if (payload.thread_id) {
        dashThread.value = payload.thread_id;
      }
      if (payload.assistant) {
        addMessage("assistant", payload.assistant.content, payload.assistant.time);
      }
      setStatus("Online");
    } catch (err) {
      pendingNode.remove();
      addMessage("assistant", "Non riesco a rispondere adesso. Verifica la connessione e riprova.");
      setStatus("Offline");
    }
  });

  dashPrompt.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      dashForm.requestSubmit();
    }
  });

  if (dashReset) {
    dashReset.addEventListener("click", () => {
      dashThread.value = "";
      dashChat.innerHTML = "";
      dashPrompt.value = "";
      setStatus("Online");
      showChatPanel();
    });
  }

  document.querySelectorAll("[data-archibald-prompt]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const text = btn.getAttribute("data-archibald-prompt") || "";
      dashPrompt.value = text;
      dashPrompt.focus();
    });
  });
}
