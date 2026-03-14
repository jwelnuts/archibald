import { registerStimulusController, withStimulusModule } from "./stimulus.js";

const DEFAULT_PREFERENCES = {
  density: "comfortable",
  accent: "blue",
  sections: ["snapshot", "widgets", "calendar", "archibald", "quick_actions"],
};

const SECTION_SET = new Set(DEFAULT_PREFERENCES.sections);

const getCsrfToken = () => {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
};

withStimulusModule(({ Controller }) => {
  class DashboardController extends Controller {
    static targets = [
      "root",
      "density",
      "accent",
      "sectionToggle",
      "quickSearch",
      "quickCard",
      "quickEmpty",
      "saveState",
    ];

    static values = {
      preferencesUrl: String,
    };

    connect() {
      this.preferences = this.loadPreferences();
      this.saveTimer = null;
      this.applyPreferences();
      this.syncControls();
      this.filterQuickActions();
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
        const haystack = String(card.dataset.dashboardSearch || card.textContent || "").toLowerCase();
        const visible = !query || haystack.includes(query);
        card.classList.toggle("dashboard-hidden", !visible);
        if (visible) {
          visibleCount += 1;
        }
      });

      if (this.hasQuickEmptyTarget) {
        this.quickEmptyTarget.hidden = visibleCount !== 0;
      }
    }

    refreshSnapshot() {
      if (!window.htmx) {
        return;
      }
      window.htmx.trigger(document.body, "dashboard:refresh");
      this.updateSaveState("Snapshot aggiornamento richiesto", "primary");
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
      const source = document.getElementById("dashboard-preferences");
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
      root.dataset.dashboardDensity = this.preferences.density;
      root.dataset.dashboardAccent = this.preferences.accent;

      const visibleSections = new Set(this.preferences.sections);
      this.element.querySelectorAll("[data-dashboard-section]").forEach((section) => {
        const key = String(section.dataset.dashboardSection || "").trim();
        if (!key) {
          return;
        }
        const isVisible = visibleSections.has(key);
        section.classList.toggle("dashboard-hidden", !isVisible);
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
        if (data && data.dashboard_preferences) {
          this.preferences = {
            density: String(data.dashboard_preferences.density || DEFAULT_PREFERENCES.density),
            accent: String(data.dashboard_preferences.accent || DEFAULT_PREFERENCES.accent),
            sections: Array.isArray(data.dashboard_preferences.sections)
              ? data.dashboard_preferences.sections
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

  registerStimulusController("dashboard", DashboardController);
}).catch(() => {});
