import { registerStimulusController, withStimulusModule } from "./stimulus.js";

const notifyError = (message) => {
  if (window.UIkit && typeof window.UIkit.notification === "function") {
    window.UIkit.notification({
      message,
      status: "danger",
      pos: "bottom-center",
      timeout: 2200,
    });
    return;
  }
  console.error(message);
};

withStimulusModule(({ Controller }) => {
  class RoutinesController extends Controller {
    connect() {
      this.STATUSES = new Set(["PLANNED", "DONE", "SKIPPED"]);
      this.activeFilter = "all";

      this.modal = document.getElementById("routine-modal");
      this.modalTitle = document.getElementById("routine-modal-title");
      this.modalFields = document.getElementById("routine-modal-fields");
      this.modalItem = document.getElementById("routine-modal-item");
      this.modalWeek = document.getElementById("routine-modal-week");
      this.modalForm = document.getElementById("routine-modal-form");
      this.todayStatsRoot = this.element.querySelector(".routines-today-stats");
      this.filterButtons = this.element.querySelectorAll("[data-routine-filter]");
      this.dayJumpButtons = this.element.querySelectorAll("[data-routine-day-jump]");
      this.daySections = this.element.querySelectorAll("[data-routine-day]");

      this.onDashboardClick = this.handleDashboardClick.bind(this);
      this.onAfterSettle = this.handleAfterSettle.bind(this);
      this.onResponseError = this.handleResponseError.bind(this);
      this.onKeydown = this.handleKeydown.bind(this);
      this.onModalCloseClick = this.closeModal.bind(this);
      this.onModalAfterRequest = this.handleModalAfterRequest.bind(this);

      this.element.addEventListener("click", this.onDashboardClick);
      document.body.addEventListener("htmx:afterSettle", this.onAfterSettle);
      document.body.addEventListener("htmx:responseError", this.onResponseError);
      document.addEventListener("keydown", this.onKeydown);

      if (this.modal) {
        this.modalCloseButtons = this.modal.querySelectorAll("[data-modal-close]");
        this.modalCloseButtons.forEach((btn) => {
          btn.addEventListener("click", this.onModalCloseClick);
        });
      }

      if (this.modalForm) {
        this.modalForm.addEventListener("htmx:afterRequest", this.onModalAfterRequest);
      }

      this.refreshCardStates();
      this.refreshTodayStats();
      this.setFilter(this.activeFilter);
      this.activateCurrentDay();
    }

    disconnect() {
      this.element.removeEventListener("click", this.onDashboardClick);
      document.body.removeEventListener("htmx:afterSettle", this.onAfterSettle);
      document.body.removeEventListener("htmx:responseError", this.onResponseError);
      document.removeEventListener("keydown", this.onKeydown);

      if (this.modalCloseButtons) {
        this.modalCloseButtons.forEach((btn) => {
          btn.removeEventListener("click", this.onModalCloseClick);
        });
      }

      if (this.modalForm) {
        this.modalForm.removeEventListener("htmx:afterRequest", this.onModalAfterRequest);
      }
    }

    handleDashboardClick(event) {
      const doneButton = event.target.closest(".routine-done-btn");
      if (doneButton) {
        event.preventDefault();
        this.openModal(doneButton);
        return;
      }

      const filterButton = event.target.closest("[data-routine-filter]");
      if (filterButton) {
        event.preventDefault();
        this.setFilter(filterButton.dataset.routineFilter || "all");
        return;
      }

      const dayJumpButton = event.target.closest("[data-routine-day-jump]");
      if (dayJumpButton) {
        event.preventDefault();
        this.jumpToDay(dayJumpButton.dataset.dayIndex, dayJumpButton);
      }
    }

    handleAfterSettle() {
      this.refreshCardStates();
      this.refreshTodayStats();
      this.applyFilters();
      this.activateCurrentDay();
    }

    handleResponseError() {
      notifyError("Salvataggio non riuscito. Riprova.");
    }

    handleModalAfterRequest(event) {
      if (event.detail && event.detail.successful) {
        this.closeModal();
      } else {
        notifyError("Salvataggio non riuscito. Riprova.");
      }
    }

    handleKeydown(event) {
      if (event.key === "Escape" && this.modal && !this.modal.hasAttribute("hidden")) {
        this.closeModal();
      }
    }

    closeModal() {
      if (!this.modal) {
        return;
      }
      this.modal.setAttribute("hidden", "");
      document.body.classList.remove("modal-open");
    }

    statusFor(container) {
      if (!container) {
        return "PLANNED";
      }
      const statusEl = container.querySelector("[data-routine-status]");
      const raw = (statusEl && (statusEl.dataset.routineStatusValue || statusEl.textContent)) || "";
      const normalized = raw.trim().toUpperCase();
      return this.STATUSES.has(normalized) ? normalized : "PLANNED";
    }

    refreshCardStates() {
      this.element.querySelectorAll("[data-routine-card]").forEach((row) => {
        const status = this.statusFor(row);
        row.dataset.status = status;

        const card = row.querySelector("[data-routine-item-id]");
        if (!card) {
          return;
        }

        card.classList.remove("is-planned", "is-done", "is-skipped");
        if (status === "DONE") {
          card.classList.add("is-done");
        } else if (status === "SKIPPED") {
          card.classList.add("is-skipped");
        } else {
          card.classList.add("is-planned");
        }
      });
    }

    refreshTodayStats() {
      if (!this.todayStatsRoot) {
        return;
      }

      const todayDate = this.todayStatsRoot.dataset.todayDate || "";
      let total = 0;
      let planned = 0;
      let done = 0;
      let skipped = 0;

      this.element.querySelectorAll(`[data-routine-card][data-day-date="${todayDate}"]`).forEach((row) => {
        total += 1;
        const status = row.dataset.status || this.statusFor(row);
        if (status === "DONE") {
          done += 1;
        } else if (status === "SKIPPED") {
          skipped += 1;
        } else {
          planned += 1;
        }
      });

      const totalEl = this.element.querySelector("#routine-today-total");
      const plannedEl = this.element.querySelector("#routine-today-planned");
      const doneEl = this.element.querySelector("#routine-today-done");
      const skippedEl = this.element.querySelector("#routine-today-skipped");
      if (totalEl) totalEl.textContent = String(total);
      if (plannedEl) plannedEl.textContent = String(planned);
      if (doneEl) doneEl.textContent = String(done);
      if (skippedEl) skippedEl.textContent = String(skipped);
    }

    applyFilters() {
      const todayDate = (this.todayStatsRoot && this.todayStatsRoot.dataset.todayDate) || "";

      this.element.querySelectorAll("[data-routine-day]").forEach((day) => {
        const dayDate = day.dataset.dayDate || "";
        const cards = Array.from(day.querySelectorAll("[data-routine-card]"));
        let visibleCards = 0;

        cards.forEach((row) => {
          const status = row.dataset.status || this.statusFor(row);
          let visible = true;

          if (this.activeFilter === "today" && dayDate !== todayDate) {
            visible = false;
          } else if (this.activeFilter === "pending" && status !== "PLANNED") {
            visible = false;
          }

          row.classList.toggle("routines-hidden", !visible);
          if (visible) {
            visibleCards += 1;
          }
        });

        let showDay = true;
        if (this.activeFilter === "today") {
          showDay = dayDate === todayDate;
        } else if (this.activeFilter === "pending") {
          showDay = cards.length > 0 && visibleCards > 0;
        }
        day.classList.toggle("routines-hidden", !showDay);
      });

      this.syncActiveDayButton();
    }

    setFilter(value) {
      this.activeFilter = value;
      this.filterButtons.forEach((button) => {
        button.classList.toggle("is-active", button.dataset.routineFilter === value);
      });
      this.applyFilters();
    }

    activateCurrentDay() {
      const todayDate = (this.todayStatsRoot && this.todayStatsRoot.dataset.todayDate) || "";
      const current = Array.from(this.daySections).find((day) => day.dataset.dayDate === todayDate);
      if (current) {
        this.setActiveDayButton(current.dataset.dayIndex || "");
      }
    }

    jumpToDay(dayIndex, button) {
      if (!dayIndex) {
        return;
      }

      const target = this.element.querySelector(`[data-routine-day][data-day-index="${dayIndex}"]`);
      if (!target) {
        return;
      }

      target.classList.add("uk-open");
      target.scrollIntoView({ behavior: "smooth", block: "start" });
      this.setActiveDayButton(dayIndex, button);
    }

    syncActiveDayButton() {
      const visibleDay = Array.from(this.daySections).find((day) => !day.classList.contains("routines-hidden"));
      if (visibleDay) {
        this.setActiveDayButton(visibleDay.dataset.dayIndex || "");
      }
    }

    setActiveDayButton(dayIndex, preferredButton = null) {
      let activeButton = preferredButton;
      this.dayJumpButtons.forEach((button) => {
        const isActive = button.dataset.dayIndex === dayIndex;
        button.classList.toggle("is-active", isActive);
        if (isActive) {
          activeButton = button;
        }
      });

      if (activeButton && typeof activeButton.scrollIntoView === "function") {
        activeButton.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
      }
    }

    openModal(button) {
      if (!this.modal || !this.modalFields || !this.modalItem || !this.modalWeek || !this.modalTitle) {
        return;
      }

      const itemId = button.getAttribute("data-item-id") || "";
      const week = button.getAttribute("data-week") || "";
      const title = button.getAttribute("data-title") || "Routine";
      const schemaId = button.getAttribute("data-schema-id") || "";
      const dataId = button.getAttribute("data-data-id") || "";

      this.modalItem.value = itemId;
      this.modalWeek.value = week;
      this.modalTitle.textContent = `Completa: ${title}`;

      let schema = [];
      let data = {};
      const schemaEl = schemaId ? document.getElementById(schemaId) : null;
      const dataEl = dataId ? document.getElementById(dataId) : null;

      if (schemaEl) {
        try {
          schema = JSON.parse(schemaEl.textContent);
        } catch (_err) {
          schema = [];
        }
      }

      if (dataEl) {
        try {
          data = JSON.parse(dataEl.textContent) || {};
        } catch (_err) {
          data = {};
        }
      }

      this.modalFields.innerHTML = "";

      if (!Array.isArray(schema) || schema.length === 0) {
        const empty = document.createElement("div");
        empty.className = "uk-alert-primary uk-padding-small";
        empty.textContent = "Nessun campo personalizzato per questa routine.";
        this.modalFields.appendChild(empty);
      } else {
        schema.forEach((field) => {
          const wrapper = document.createElement("div");
          wrapper.className = "field uk-margin-small-bottom";

          const label = document.createElement("label");
          label.textContent = field.label || field.name || "Campo";

          const fieldName = field.name || "custom";
          const inputId = `modal_${itemId}_${fieldName}`;
          label.setAttribute("for", inputId);

          let input;
          const value = data[fieldName];

          if (field.type === "textarea") {
            input = document.createElement("textarea");
            input.className = "uk-textarea uk-form-small";
            input.rows = 3;
            input.value = value || "";
          } else if (field.type === "select") {
            input = document.createElement("select");
            input.className = "uk-select uk-form-small";

            const placeholder = document.createElement("option");
            placeholder.value = "";
            placeholder.textContent = "Seleziona...";
            input.appendChild(placeholder);

            const options = Array.isArray(field.options) ? field.options : [];
            options.forEach((option) => {
              const opt = document.createElement("option");
              if (Array.isArray(option)) {
                opt.value = option[0];
                opt.textContent = option[1];
              } else if (option && typeof option === "object") {
                opt.value = option.value || option.id || option.label || "";
                opt.textContent = option.label || option.value || option.id || "";
              } else {
                opt.value = option;
                opt.textContent = option;
              }
              if (value !== undefined && String(value) === String(opt.value)) {
                opt.selected = true;
              }
              input.appendChild(opt);
            });
          } else {
            input = document.createElement("input");
            input.className = "uk-input uk-form-small";
            if (["number", "time", "date", "checkbox"].includes(field.type)) {
              input.type = field.type;
            } else {
              input.type = "text";
            }

            if (input.type === "checkbox") {
              input.className = "uk-checkbox";
              input.checked = Boolean(value);
            } else if (value !== undefined && value !== null) {
              input.value = value;
            }
          }

          input.id = inputId;
          input.name = `data_${fieldName}`;
          if (field.placeholder) {
            input.placeholder = field.placeholder;
          }
          if (field.required) {
            input.required = true;
          }

          wrapper.appendChild(label);
          wrapper.appendChild(input);
          this.modalFields.appendChild(wrapper);
        });
      }

      this.modal.removeAttribute("hidden");
      document.body.classList.add("modal-open");
    }
  }

  registerStimulusController("routines", RoutinesController);
}).catch(() => {});
