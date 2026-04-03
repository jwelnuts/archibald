import { registerStimulusController, withStimulusModule } from "@core/stimulus.js";

const DEFAULT_PREFERENCES = {
  density: "comfortable",
  accent: "blue",
  sections: ["snapshot", "panel", "forms", "quick_actions"],
};

const SECTION_SET = new Set(DEFAULT_PREFERENCES.sections);

const getCsrfToken = () => {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
};

withStimulusModule(({ Controller }) => {
  class AgendaController extends Controller {
    static targets = [
      "root",
      "density",
      "accent",
      "sectionToggle",
      "quickSearch",
      "quickCard",
      "quickEmpty",
      "saveState",
      "monthField",
      "selectedField",
      "panel",
      "snapshot",
    ];

    static values = {
      preferencesUrl: String,
    };

    connect() {
      this.preferences = this.loadPreferences();
      this.saveTimer = null;
      this.panelFilter = "all";

      this.onAfterSwap = this.handleAfterSwap.bind(this);
      this.onChange = this.handleChange.bind(this);
      document.body.addEventListener("htmx:afterSwap", this.onAfterSwap);
      this.element.addEventListener("change", this.onChange);

      this.applyUIKitFieldClasses();
      this.initDatePickers();
      this.applyPreferences();
      this.syncControls();
      this.filterQuickActions();
      this.syncPanelState();
      this.applyPanelFilter();
      this.syncPlannerProjectField();
      this.syncPlannerCategoryField();
    }

    disconnect() {
      document.body.removeEventListener("htmx:afterSwap", this.onAfterSwap);
      this.element.removeEventListener("change", this.onChange);
    }

    handleAfterSwap(event) {
      const target = event && event.detail ? event.detail.target : null;
      if (!target) {
        return;
      }
      if (target.id === "agenda-live-panel") {
        this.syncPanelState();
        this.applyPanelFilter();
        const xhr = event.detail && event.detail.xhr ? event.detail.xhr : null;
        const triggerHeader = xhr && typeof xhr.getResponseHeader === "function"
          ? String(xhr.getResponseHeader("HX-Trigger") || "")
          : "";
        if (window.htmx && triggerHeader.indexOf("agenda:refresh-snapshot") === -1) {
          window.htmx.trigger(document.body, "agenda:refresh-snapshot");
        }
      }
    }

    handleChange(event) {
      const targetId = String((event.target && event.target.id) || "");
      if (targetId === "id_planner-project_choice") {
        this.syncPlannerProjectField();
      }
      if (targetId === "id_planner-category_choice") {
        this.syncPlannerCategoryField();
      }
    }

    densityChanged(event) {
      const value = String(event.target.value || "").trim().toLowerCase();
      this.preferences.density = value || DEFAULT_PREFERENCES.density;
      this.applyPreferences();
      this.queueSave();
    }

    accentChanged(event) {
      const value = String(event.target.value || "").trim().toLowerCase();
      this.preferences.accent = value || DEFAULT_PREFERENCES.accent;
      this.applyPreferences();
      this.queueSave();
    }

    sectionChanged() {
      const sections = [];
      this.sectionToggleTargets.forEach((toggle) => {
        const key = String(toggle.dataset.sectionKey || "").trim();
        if (!key || !SECTION_SET.has(key)) {
          return;
        }
        if (toggle.checked) {
          sections.push(key);
        }
      });
      this.preferences.sections = sections.length ? sections : [...DEFAULT_PREFERENCES.sections];
      this.applyPreferences();
      this.queueSave();
    }

    filterQuickActions() {
      if (!this.hasQuickCardTarget) {
        return;
      }

      const query = this.hasQuickSearchTarget
        ? String(this.quickSearchTarget.value || "").trim().toLowerCase()
        : "";
      let visibleCount = 0;

      this.quickCardTargets.forEach((card) => {
        const haystack = String(
          card.dataset.agendaSearch || card.dataset.search || card.textContent || ""
        ).toLowerCase();
        const visible = !query || haystack.includes(query);
        card.classList.toggle("agenda-hidden", !visible);
        if (visible) {
          visibleCount += 1;
        }
      });

      if (this.hasQuickEmptyTarget) {
        this.quickEmptyTarget.hidden = visibleCount !== 0;
      }
    }

    filterPanelEvents(event) {
      const button = event.target.closest("[data-agenda-filter]");
      if (!button) {
        return;
      }
      this.panelFilter = String(button.dataset.agendaFilter || "all");
      this.applyPanelFilter();
    }

    refreshSnapshot() {
      if (!window.htmx) {
        return;
      }
      window.htmx.trigger(document.body, "agenda:refresh-snapshot");
      this.updateSaveState("Snapshot aggiornato", "primary");
    }

    resetPreferences() {
      this.preferences = {
        density: DEFAULT_PREFERENCES.density,
        accent: DEFAULT_PREFERENCES.accent,
        sections: [...DEFAULT_PREFERENCES.sections],
      };
      this.applyPreferences();
      this.syncControls();
      this.queueSave(60);
    }

    saveNow() {
      this.persistPreferences(false);
    }

    loadPreferences() {
      let payload = {};
      const source = document.getElementById("agenda-preferences");
      if (source) {
        try {
          payload = JSON.parse(source.textContent || "{}");
        } catch (_err) {
          payload = {};
        }
      }

      const density = String(payload.density || DEFAULT_PREFERENCES.density).toLowerCase();
      const accent = String(payload.accent || DEFAULT_PREFERENCES.accent).toLowerCase();
      const sectionsRaw = Array.isArray(payload.sections) ? payload.sections : [];
      const sections = sectionsRaw
        .map((row) => String(row || "").trim())
        .filter((row, idx, arr) => row && SECTION_SET.has(row) && arr.indexOf(row) === idx);

      return {
        density: density || DEFAULT_PREFERENCES.density,
        accent: accent || DEFAULT_PREFERENCES.accent,
        sections: sections.length ? sections : [...DEFAULT_PREFERENCES.sections],
      };
    }

    syncControls() {
      if (this.hasDensityTarget) {
        this.densityTarget.value = this.preferences.density;
      }
      if (this.hasAccentTarget) {
        this.accentTarget.value = this.preferences.accent;
      }

      const visible = new Set(this.preferences.sections);
      this.sectionToggleTargets.forEach((toggle) => {
        const key = String(toggle.dataset.sectionKey || "").trim();
        toggle.checked = visible.has(key);
      });
    }

    applyPreferences() {
      const root = this.hasRootTarget ? this.rootTarget : this.element;
      root.dataset.agendaDensity = this.preferences.density;
      root.dataset.agendaAccent = this.preferences.accent;

      const visibleSections = new Set(this.preferences.sections);
      this.element.querySelectorAll("[data-agenda-section]").forEach((section) => {
        const key = String(section.dataset.agendaSection || "").trim();
        if (!key) {
          return;
        }
        section.classList.toggle("agenda-hidden", !visibleSections.has(key));
      });
    }

    queueSave(delay = 220) {
      if (this.saveTimer) {
        window.clearTimeout(this.saveTimer);
      }
      this.saveTimer = window.setTimeout(() => {
        this.persistPreferences(true);
      }, delay);
    }

    async persistPreferences(silent = false) {
      if (!this.hasPreferencesUrlValue || !this.preferencesUrlValue) {
        return;
      }

      const payload = {
        density: this.preferences.density,
        accent: this.preferences.accent,
        sections: this.preferences.sections,
      };

      try {
        const response = await fetch(this.preferencesUrlValue, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
            "X-Requested-With": "XMLHttpRequest",
          },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          this.updateSaveState("Errore salvataggio preferenze", "danger", silent);
          return;
        }

        const data = await response.json();
        if (data && data.agenda_preferences) {
          this.preferences = {
            density: String(data.agenda_preferences.density || DEFAULT_PREFERENCES.density),
            accent: String(data.agenda_preferences.accent || DEFAULT_PREFERENCES.accent),
            sections: Array.isArray(data.agenda_preferences.sections)
              ? data.agenda_preferences.sections
              : [...DEFAULT_PREFERENCES.sections],
          };
          this.syncControls();
          this.applyPreferences();
        }
        this.updateSaveState("Preferenze salvate", "success", silent);
      } catch (_err) {
        this.updateSaveState("Salvataggio non disponibile", "warning", silent);
      }
    }

    syncPanelState() {
      const panel = this.hasPanelTarget ? this.panelTarget : this.element.querySelector("#agenda-live-panel");
      if (!panel) {
        return;
      }

      const month = String(panel.dataset.month || "").trim();
      const selected = String(panel.dataset.selected || "").trim();

      this.monthFieldTargets.forEach((field) => {
        field.value = month;
      });
      this.selectedFieldTargets.forEach((field) => {
        field.value = selected;
      });

      const todoDateField = this.element.querySelector("#id_due_date");
      if (todoDateField && selected) {
        todoDateField.value = selected;
      }
      const workDateField = this.element.querySelector("#id_work_date");
      if (workDateField && selected) {
        workDateField.value = selected;
      }
      const plannerDateField = this.element.querySelector("#id_planner-due_date");
      if (plannerDateField && selected) {
        plannerDateField.value = selected;
      }

      if (this.hasSnapshotTarget && month && selected) {
        const url = `/agenda/snapshot?month=${encodeURIComponent(month)}&selected=${encodeURIComponent(selected)}`;
        this.snapshotTarget.setAttribute("hx-get", url);
        if (window.htmx && typeof window.htmx.process === "function") {
          window.htmx.process(this.snapshotTarget);
        }
      }
    }

    applyPanelFilter() {
      const panel = this.hasPanelTarget ? this.panelTarget : this.element.querySelector("#agenda-live-panel");
      if (!panel) {
        return;
      }

      panel.querySelectorAll("[data-agenda-filter]").forEach((button) => {
        button.classList.toggle("is-active", button.dataset.agendaFilter === this.panelFilter);
      });

      const rows = panel.querySelectorAll("[data-agenda-event-row]");
      rows.forEach((row) => {
        const kind = String(row.dataset.kind || "").trim();
        let visible = true;
        if (this.panelFilter === "agenda") {
          visible = kind === "agenda_activity" || kind === "agenda_reminder";
        } else if (this.panelFilter !== "all") {
          visible = kind === this.panelFilter;
        }
        row.classList.toggle("agenda-hidden-row", !visible);
      });
    }

    syncPlannerProjectField() {
      const select = this.element.querySelector("#id_planner-project_choice");
      const row = this.element.querySelector("[data-agenda-planner-project-row]");
      if (!select || !row) {
        return;
      }

      const show = select.value === "__new__";
      row.classList.toggle("agenda-hidden", !show);
      row.querySelectorAll("input, select, textarea").forEach((field) => {
        const type = (field.getAttribute("type") || "").toLowerCase();
        if (type === "hidden") {
          return;
        }
        field.disabled = !show;
        if (!show && field.tagName === "INPUT") {
          field.value = "";
        }
      });
    }

    syncPlannerCategoryField() {
      const select = this.element.querySelector("#id_planner-category_choice");
      const row = this.element.querySelector("[data-agenda-planner-category-row]");
      if (!select || !row) {
        return;
      }

      const show = select.value === "__new__";
      row.classList.toggle("agenda-hidden", !show);
      row.querySelectorAll("input, select, textarea").forEach((field) => {
        const type = (field.getAttribute("type") || "").toLowerCase();
        if (type === "hidden") {
          return;
        }
        field.disabled = !show;
        if (!show && field.tagName === "INPUT") {
          field.value = "";
        }
      });
    }

    applyUIKitFieldClasses() {
      this.element.querySelectorAll("select").forEach((el) => {
        el.classList.add("uk-select", "uk-form-small");
      });

      this.element.querySelectorAll("textarea").forEach((el) => {
        el.classList.add("uk-textarea", "uk-form-small");
      });

      this.element.querySelectorAll("input").forEach((el) => {
        const type = (el.getAttribute("type") || "text").toLowerCase();
        if (type === "hidden" || type === "checkbox" || type === "radio" || type === "submit" || type === "button") {
          return;
        }
        el.classList.add("uk-input", "uk-form-small");
      });
    }

    initDatePickers() {
      if (!window.flatpickr) {
        return;
      }

      this.element.querySelectorAll(".date-field").forEach((el) => {
        if (el._flatpickr) {
          return;
        }
        window.flatpickr(el, {
          dateFormat: "Y-m-d",
          allowInput: true,
        });
      });
    }

    updateSaveState(message, status = "primary", silent = false) {
      if (this.hasSaveStateTarget) {
        this.saveStateTarget.textContent = message;
      }
      if (!silent && window.UIkit && typeof window.UIkit.notification === "function") {
        window.UIkit.notification({
          message,
          status,
          pos: "bottom-center",
          timeout: 1400,
        });
      }
    }
  }

  registerStimulusController("agenda", AgendaController);
}).catch(() => {});
