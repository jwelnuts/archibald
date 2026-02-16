const portal = document.getElementById("portal");

const setupPortalDrag = () => {
  if (!portal) return;
  let dragging = null;

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

  portal.querySelectorAll(".portlet").forEach((card) => {
    card.setAttribute("draggable", "true");
    card.addEventListener("dragstart", (event) => {
      dragging = card;
      card.classList.add("is-dragging");
      portal.classList.add("is-dragging");
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", "");
      }
    });
    card.addEventListener("dragend", () => {
      card.classList.remove("is-dragging");
      portal.classList.remove("is-dragging");
      dragging = null;
    });
  });

  portal.addEventListener("dragover", (event) => {
    if (!dragging) return;
    event.preventDefault();
    const after = getDragAfterElement(portal, event.clientY);
    if (!after) {
      portal.appendChild(dragging);
    } else if (after !== dragging) {
      portal.insertBefore(dragging, after);
    }
  });
};

const setupPortalFilter = () => {
  if (!portal) return;
  const filterWrap = document.querySelector("[data-portal-filter]");
  if (!filterWrap) return;

  const chips = filterWrap.querySelectorAll(".filter-chip");
  const applyFilter = (filter) => {
    portal.querySelectorAll(".portlet").forEach((card) => {
      const group = card.getAttribute("data-group");
      const visible = filter === "all" || group === filter;
      card.classList.toggle("is-hidden", !visible);
    });
  };

  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      chips.forEach((btn) => btn.classList.remove("active"));
      chip.classList.add("active");
      const filter = chip.getAttribute("data-filter") || "all";
      applyFilter(filter);
    });
  });
};

setupPortalDrag();
setupPortalFilter();

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

if (dashForm && dashChat && dashPrompt && dashThread) {
  const addMessage = (role, content, time) => {
    const wrapper = document.createElement("div");
    wrapper.className = `chat-message ${role}`;
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
  };

  const getCsrfToken = () => {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : "";
  };

  dashForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = dashPrompt.value.trim();
    if (!text) return;
    addMessage("user", text);
    dashPrompt.value = "";
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
      if (!resp.ok) return;
      const payload = await resp.json();
      if (payload.thread_id) {
        dashThread.value = payload.thread_id;
      }
      if (payload.assistant) {
        addMessage("assistant", payload.assistant.content, payload.assistant.time);
      }
    } catch (err) {
      // ignore
    }
  });

  if (dashReset) {
    dashReset.addEventListener("click", () => {
      dashThread.value = "";
      dashChat.innerHTML = "";
      dashPrompt.value = "";
      dashPrompt.focus();
    });
  }
}
