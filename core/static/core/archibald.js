import { registerStimulusController, withStimulusModule } from "./stimulus.js";

withStimulusModule(({ Controller }) => {
  class ArchibaldChatController extends Controller {
    static targets = [
      "form",
      "chat",
      "editor",
      "promptField",
      "modeField",
      "threadField",
      "dayField",
      "emptyState",
    ];

    static values = {
      mode: String,
      messagesUrl: String,
      favoriteUrl: String,
    };

    connect() {
      this.loadingOlder = false;
      this.exhaustedOlder = false;
      this.promptButtons = Array.from(this.element.querySelectorAll("[data-prompt]"));
      this.onPromptClick = this.handlePromptClick.bind(this);
      this.promptButtons.forEach((button) => {
        button.addEventListener("click", this.onPromptClick);
      });

      this.initQuill();
      this.scrollToBottom();
    }

    disconnect() {
      if (this.promptButtons && this.onPromptClick) {
        this.promptButtons.forEach((button) => {
          button.removeEventListener("click", this.onPromptClick);
        });
      }
      this.promptButtons = [];
      this.onPromptClick = null;
      this.quill = null;
    }

    initQuill() {
      this.quill = null;
      if (!this.hasEditorTarget || !window.Quill) {
        return;
      }
      this.quill = new window.Quill("#archibald-editor", {
        theme: "snow",
        modules: {
          toolbar: "#archibald-editor-toolbar",
        },
      });
      if (this.hasPromptFieldTarget) {
        this.promptFieldTarget.required = false;
      }
    }

    handlePromptClick(event) {
      event.preventDefault();
      const text = event.currentTarget?.dataset?.prompt || "";
      if (!text) {
        return;
      }
      this.setPrompt(text);
    }

    setPrompt(text) {
      if (this.quill) {
        this.quill.setText(text);
        this.quill.focus();
        return;
      }
      if (this.hasPromptFieldTarget) {
        this.promptFieldTarget.value = text;
        this.promptFieldTarget.focus();
      }
    }

    getPromptText() {
      if (this.quill) {
        return (this.quill.getText() || "").trim();
      }
      if (this.hasPromptFieldTarget) {
        return (this.promptFieldTarget.value || "").trim();
      }
      return "";
    }

    clearPrompt() {
      if (this.quill) {
        this.quill.setText("");
        this.quill.focus();
        return;
      }
      if (this.hasPromptFieldTarget) {
        this.promptFieldTarget.value = "";
        this.promptFieldTarget.focus();
      }
    }

    currentMode() {
      if (this.hasModeFieldTarget && this.modeFieldTarget.value) {
        return this.modeFieldTarget.value;
      }
      return this.modeValue || "diary";
    }

    currentDay() {
      if (this.hasDayFieldTarget && this.dayFieldTarget.value) {
        return this.dayFieldTarget.value;
      }
      if (this.hasChatTarget) {
        return this.chatTarget.getAttribute("data-day") || "";
      }
      return "";
    }

    currentThreadId() {
      if (this.hasThreadFieldTarget && this.threadFieldTarget.value) {
        return this.threadFieldTarget.value;
      }
      if (this.hasChatTarget) {
        return this.chatTarget.getAttribute("data-thread-id") || "";
      }
      return "";
    }

    getCsrfToken() {
      const match = document.cookie.match(/csrftoken=([^;]+)/);
      return match ? match[1] : "";
    }

    notify(message, status = "primary") {
      if (window.UIkit && typeof window.UIkit.notification === "function") {
        window.UIkit.notification({
          message,
          status,
          pos: "bottom-center",
          timeout: 1800,
        });
        return;
      }
      window.alert(message);
    }

    removeEmptyState() {
      if (this.hasEmptyStateTarget) {
        this.emptyStateTarget.remove();
      }
      if (!this.hasChatTarget) {
        return;
      }
      const systemMsg = this.chatTarget.querySelector(".chat-message.system");
      if (systemMsg) {
        systemMsg.remove();
      }
    }

    scrollToBottom() {
      if (!this.hasChatTarget) {
        return;
      }
      this.chatTarget.scrollTop = this.chatTarget.scrollHeight;
    }

    formatDayLabel(day) {
      if (!day) {
        return "";
      }
      try {
        const date = new Date(`${day}T00:00:00`);
        return date.toLocaleDateString("it-IT", { day: "2-digit", month: "short", year: "numeric" });
      } catch (_) {
        return day;
      }
    }

    buildDaySection(day) {
      const wrapper = document.createElement("div");
      wrapper.className = "diary-day";
      wrapper.setAttribute("data-day", day);

      const head = document.createElement("div");
      head.className = "diary-day-head";
      const label = document.createElement("span");
      label.textContent = "Capitolo";
      const title = document.createElement("strong");
      title.textContent = this.formatDayLabel(day);
      head.appendChild(label);
      head.appendChild(title);

      const page = document.createElement("div");
      page.className = "diary-page";

      wrapper.appendChild(head);
      wrapper.appendChild(page);
      return { wrapper, page };
    }

    buildMessageNode(msg, day) {
      const wrapper = document.createElement("div");
      wrapper.className = `chat-message ${msg.role}`;
      if (day) {
        wrapper.setAttribute("data-day", day);
      }

      const bubble = document.createElement("div");
      bubble.className = "chat-bubble";

      const role = document.createElement("div");
      role.className = "chat-role";
      role.textContent = msg.role ? msg.role.charAt(0).toUpperCase() + msg.role.slice(1) : "";

      const text = document.createElement("div");
      text.className = "chat-text";
      text.textContent = msg.content || "";

      const meta = document.createElement("div");
      meta.className = "chat-meta";
      const time = document.createElement("span");
      time.className = "chat-time";
      time.textContent =
        msg.time || new Date().toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });

      const fav = document.createElement("button");
      fav.className = `chat-fav${msg.is_favorite ? " active" : ""}`;
      if (msg.id) {
        fav.setAttribute("data-id", msg.id);
      }
      fav.setAttribute("type", "button");
      fav.setAttribute("aria-label", "Preferito");
      fav.textContent = "★";

      meta.appendChild(time);
      meta.appendChild(fav);
      bubble.appendChild(role);
      bubble.appendChild(text);
      bubble.appendChild(meta);
      wrapper.appendChild(bubble);
      return wrapper;
    }

    ensureDayPage(day) {
      if (!this.hasChatTarget || !day) {
        return null;
      }
      const existing = this.chatTarget.querySelector(`.diary-day[data-day="${day}"]`);
      if (existing) {
        return existing.querySelector(".diary-page");
      }
      const section = this.buildDaySection(day);
      this.chatTarget.appendChild(section.wrapper);
      return section.page;
    }

    appendMessage(msg) {
      if (!this.hasChatTarget) {
        return;
      }
      const day = msg.day || this.currentDay();
      const page = this.ensureDayPage(day);
      if (!page) {
        return;
      }
      page.appendChild(this.buildMessageNode(msg, day));
      if (msg.id) {
        const oldestId = this.chatTarget.getAttribute("data-oldest-id");
        if (!oldestId || Number(msg.id) < Number(oldestId)) {
          this.chatTarget.setAttribute("data-oldest-id", String(msg.id));
        }
      }
      this.scrollToBottom();
    }

    prependOlder(messages) {
      if (!this.hasChatTarget || !Array.isArray(messages) || !messages.length) {
        return;
      }

      const firstDayEl = this.chatTarget.querySelector(".diary-day");
      const firstDay = firstDayEl ? firstDayEl.getAttribute("data-day") : null;

      const previousHeight = this.chatTarget.scrollHeight;
      const fragment = document.createDocumentFragment();
      let currentDay = null;
      let currentSection = null;

      messages.forEach((msg) => {
        const day = msg.day || "";
        if (!day) {
          return;
        }

        if (day !== currentDay) {
          const existingFirst = day === firstDay ? this.chatTarget.querySelector(`.diary-day[data-day="${day}"]`) : null;
          if (existingFirst) {
            currentSection = { page: existingFirst.querySelector(".diary-page") };
          } else {
            currentSection = this.buildDaySection(day);
            fragment.appendChild(currentSection.wrapper);
          }
          currentDay = day;
        }

        if (currentSection && currentSection.page) {
          currentSection.page.appendChild(this.buildMessageNode(msg, day));
        }
      });

      this.chatTarget.insertBefore(fragment, this.chatTarget.firstChild);
      this.chatTarget.scrollTop = this.chatTarget.scrollHeight - previousHeight;
    }

    updateUrlFromPayload(payload) {
      if (!payload) {
        return;
      }
      const mode = payload.mode || this.currentMode();
      const params = new URLSearchParams(window.location.search || "");
      params.set("mode", mode);

      if (mode === "temp") {
        const threadId = payload.thread?.id || this.currentThreadId();
        if (threadId) {
          params.set("thread", String(threadId));
        }
        params.delete("day");
      } else {
        const day = payload.user?.day || this.currentDay();
        if (day) {
          params.set("day", day);
        }
        params.delete("thread");
      }

      const query = params.toString();
      const nextUrl = query ? `${window.location.pathname}?${query}` : window.location.pathname;
      window.history.replaceState({}, "", nextUrl);
    }

    updateStateFromPayload(payload) {
      if (!payload) {
        return;
      }

      if (payload.mode) {
        this.modeValue = payload.mode;
        if (this.hasModeFieldTarget) {
          this.modeFieldTarget.value = payload.mode;
        }
      }

      if (payload.thread && payload.thread.id) {
        if (this.hasThreadFieldTarget) {
          this.threadFieldTarget.value = String(payload.thread.id);
        }
        if (this.hasChatTarget) {
          this.chatTarget.setAttribute("data-thread-id", String(payload.thread.id));
        }
      }

      if (payload.user && payload.user.day) {
        if (this.hasChatTarget) {
          this.chatTarget.setAttribute("data-day", payload.user.day);
        }
        if (this.hasDayFieldTarget) {
          this.dayFieldTarget.value = payload.user.day;
        }
      }

      this.updateUrlFromPayload(payload);
    }

    async submit(event) {
      event.preventDefault();
      if (!this.hasFormTarget) {
        return;
      }

      const text = this.getPromptText();
      if (!text) {
        this.notify("Scrivi un messaggio per Archibald.", "warning");
        return;
      }

      if (this.hasPromptFieldTarget) {
        this.promptFieldTarget.value = text;
      }

      let optimisticDay = this.currentDay();
      if (this.currentMode() === "diary") {
        optimisticDay = new Date().toISOString().slice(0, 10);
        if (this.hasDayFieldTarget) {
          this.dayFieldTarget.value = optimisticDay;
        }
        if (this.hasChatTarget) {
          this.chatTarget.setAttribute("data-day", optimisticDay);
        }
      }

      this.removeEmptyState();
      this.appendMessage({ role: "user", content: text, day: optimisticDay });
      this.clearPrompt();

      const body = new FormData(this.formTarget);
      try {
        const response = await fetch(this.formTarget.action || window.location.href, {
          method: "POST",
          body,
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": this.getCsrfToken(),
          },
          credentials: "same-origin",
        });

        if (!response.ok) {
          this.notify("Risposta non valida da Archibald.", "danger");
          return;
        }

        const payload = await response.json();
        this.updateStateFromPayload(payload);

        if (payload && payload.assistant) {
          this.appendMessage(payload.assistant);
        }
      } catch (_) {
        this.notify("Connessione non riuscita. Riprova.", "danger");
      }
    }

    async onChatClick(event) {
      const target = event.target.closest(".chat-fav");
      if (!target || !target.getAttribute("data-id")) {
        return;
      }

      const formData = new FormData();
      formData.append("id", target.getAttribute("data-id"));

      try {
        const response = await fetch(this.favoriteUrlValue || "/archibald/favorite", {
          method: "POST",
          body: formData,
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": this.getCsrfToken(),
          },
          credentials: "same-origin",
        });

        if (!response.ok) {
          return;
        }

        const result = await response.json();
        if (result && result.ok) {
          target.classList.toggle("active", Boolean(result.is_favorite));
        }
      } catch (_) {
        // ignore favorite errors
      }
    }

    async onScroll() {
      if (!this.hasChatTarget || this.loadingOlder || this.exhaustedOlder) {
        return;
      }
      if (this.chatTarget.scrollTop >= 40) {
        return;
      }

      const oldest = this.chatTarget.getAttribute("data-oldest-id");
      if (!oldest) {
        return;
      }

      this.loadingOlder = true;
      try {
        const params = new URLSearchParams();
        params.set("before", oldest);
        params.set("mode", this.currentMode());

        if (this.currentMode() === "temp") {
          const threadId = this.currentThreadId();
          if (threadId) {
            params.set("thread", threadId);
          }
        } else {
          const day = this.currentDay();
          if (day) {
            params.set("day", day);
          }
        }

        const url = `${this.messagesUrlValue || "/archibald/messages"}?${params.toString()}`;
        const response = await fetch(url, { credentials: "same-origin" });
        if (!response.ok) {
          return;
        }

        const payload = await response.json();
        const rows = Array.isArray(payload.messages) ? payload.messages : [];
        if (!rows.length) {
          this.exhaustedOlder = true;
          return;
        }

        this.chatTarget.setAttribute("data-oldest-id", String(rows[0].id));
        this.prependOlder(rows);
      } catch (_) {
        // silent for scroll loading
      } finally {
        this.loadingOlder = false;
      }
    }
  }

  registerStimulusController("archibald-chat", ArchibaldChatController);
}).catch(() => {});
