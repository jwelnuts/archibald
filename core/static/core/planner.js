import { registerStimulusController } from "./stimulus.js";

registerStimulusController("planner", class extends window.StimulusModule.Controller {
  static targets = ["categorySelect", "categoryName", "projectSelect", "projectName", "form", "list"];

  connect() {
    this._boundOnCategoryChange = this._onCategoryChange.bind(this);
    this._boundOnProjectChange = this._onProjectChange.bind(this);
    if (this.hasCategorySelectTarget) {
      this.categorySelectTarget.addEventListener("change", this._boundOnCategoryChange);
    }
    if (this.hasProjectSelectTarget) {
      this.projectSelectTarget.addEventListener("change", this._boundOnProjectChange);
    }
    // Sync initial state
    requestAnimationFrame(() => {
      this._syncCategory();
      this._syncProject();
    });
  }

  disconnect() {
    if (this.hasCategorySelectTarget) {
      this.categorySelectTarget.removeEventListener("change", this._boundOnCategoryChange);
    }
    if (this.hasProjectSelectTarget) {
      this.projectSelectTarget.removeEventListener("change", this._boundOnProjectChange);
    }
  }

  _onCategoryChange() {
    this._syncCategory();
  }

  _onProjectChange() {
    this._syncProject();
  }

  _syncCategory() {
    if (!this.hasCategorySelectTarget || !this.hasCategoryNameTarget) return;
    const show = this.categorySelectTarget.value === "__new__";
    this.categoryNameTarget.style.display = show ? "block" : "none";
    if (!show) this.categoryNameTarget.value = "";
  }

  _syncProject() {
    if (!this.hasProjectSelectTarget || !this.hasProjectNameTarget) return;
    const show = this.projectSelectTarget.value === "__new__";
    this.projectNameTarget.style.display = show ? "block" : "none";
    if (!show) this.projectNameTarget.value = "";
  }

  async deleteItem(event) {
    event.preventDefault();
    const btn = event.currentTarget;
    const itemId = btn.dataset.plannerId;
    if (!itemId) return;
    if (!confirm("Eliminare questa voce?")) return;

    const csrf = this._getCsrf();
    try {
      const res = await fetch(`/planner/api/delete/${itemId}/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
          "HX-Request": "true",
        },
      });
      if (res.ok) {
        const row = document.getElementById(`planner-item-${itemId}`);
        if (row) row.remove();
        // Refresh counts
        window.htmx?.trigger("#planner-dashboard-form", "submit");
      } else {
        alert("Errore durante l'eliminazione.");
      }
    } catch (_e) {
      alert("Errore di rete.");
    }
  }

  async toggleStatus(event) {
    event.preventDefault();
    const btn = event.currentTarget;
    const itemId = btn.dataset.plannerId;
    const newStatus = btn.dataset.status;
    if (!itemId || !newStatus) return;

    const csrf = this._getCsrf();
    try {
      const res = await fetch(`/planner/api/toggle-status/${itemId}/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
          "HX-Request": "true",
        },
        body: JSON.stringify({ status: newStatus }),
        contentType: "application/json",
      });
      if (res.ok) {
        // Re-fetch the dashboard content
        window.htmx?.trigger("#planner-dashboard-form", "submit");
      } else {
        alert("Errore durante l'aggiornamento.");
      }
    } catch (_e) {
      alert("Errore di rete.");
    }
  }

  _getCsrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : "";
  }
});