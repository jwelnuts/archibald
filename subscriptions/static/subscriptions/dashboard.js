import { registerStimulusController, withStimulusModule } from "@core/stimulus.js";

const notify = (message, status = "primary") => {
  if (window.UIkit && typeof window.UIkit.notification === "function") {
    window.UIkit.notification({
      message,
      status,
      pos: "bottom-center",
      timeout: 1800,
    });
  }
};

withStimulusModule(({ Controller }) => {
  class SubscriptionsDashboardController extends Controller {
    static targets = ["payForm", "occurrenceInput", "subscriptionInput", "dueDateInput", "nameInput", "dateInput", "amountInput"];

    connect() {
      this.modalElement = document.getElementById("subs-pay-modal");
      this.handleClick = this.onClick.bind(this);
      this.handlePaid = this.onPaid.bind(this);
      this.handleAfterSwap = this.onAfterSwap.bind(this);
      this.handleResponseError = this.onResponseError.bind(this);

      document.body.addEventListener("click", this.handleClick);
      document.body.addEventListener("subs:paid", this.handlePaid);
      document.body.addEventListener("htmx:afterSwap", this.handleAfterSwap);
      document.body.addEventListener("htmx:responseError", this.handleResponseError);
    }

    disconnect() {
      document.body.removeEventListener("click", this.handleClick);
      document.body.removeEventListener("subs:paid", this.handlePaid);
      document.body.removeEventListener("htmx:afterSwap", this.handleAfterSwap);
      document.body.removeEventListener("htmx:responseError", this.handleResponseError);
    }

    onClick(event) {
      const trigger = event.target.closest("[data-subs-pay-trigger]");
      if (!trigger) {
        return;
      }
      event.preventDefault();
      this.openPayModal(trigger);
    }

    onPaid(event) {
      this.resetForm();
      this.hideModal();
      const detail = event.detail || {};
      if (detail.message) {
        notify(detail.message, "success");
      }
    }

    onAfterSwap(event) {
      const target = event.target;
      if (!target || target.id !== "subs-dashboard-board") {
        return;
      }
      if (window.htmx && typeof window.htmx.process === "function") {
        window.htmx.process(target);
      }
    }

    onResponseError() {
      notify("Operazione non riuscita. Riprova.", "danger");
    }

    _modalEl() {
      return this.modalElement || document.getElementById("subs-pay-modal");
    }

    _q(sel) {
      const m = this._modalEl();
      return m ? m.querySelector(sel) : null;
    }

    openPayModal(trigger) {
      const modal = this._modalEl();
      if (!modal) return;

      const set = (sel, val) => { const el = modal.querySelector(sel); if (el) el.value = val; };
      set('[name="occurrence_id"]',   trigger.dataset.occurrenceId   || "");
      set('[name="subscription_id"]', trigger.dataset.subscriptionId || "");
      set('[name="due_date"]',        trigger.dataset.dueDate        || "");
      set('[data-subs-dashboard-target="nameInput"]',   trigger.dataset.subscriptionName || "");
      set('[data-subs-dashboard-target="dateInput"]',   trigger.dataset.dueDate          || "");
      set('[data-subs-dashboard-target="amountInput"]', trigger.dataset.amount           || "");

      if (window.UIkit) window.UIkit.modal(modal).show();
    }

    resetForm() {
      const modal = this._modalEl();
      if (!modal) return;
      const form = modal.querySelector("form");
      if (form) form.reset();
      ['[name="occurrence_id"]', '[name="subscription_id"]', '[name="due_date"]'].forEach(sel => {
        const el = modal.querySelector(sel);
        if (el) el.value = "";
      });
    }

    hideModal() {
      if (!this.modalElement || !window.UIkit) {
        return;
      }
      const instance = window.UIkit.modal(this.modalElement);
      if (instance) {
        instance.hide();
      }
    }
  }

  registerStimulusController("subs-dashboard", SubscriptionsDashboardController);
});
