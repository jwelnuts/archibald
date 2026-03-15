import { registerStimulusController, withStimulusModule } from "../core/stimulus.js";

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

    openPayModal(trigger) {
      if (!this.hasPayFormTarget) {
        return;
      }
      if (this.hasOccurrenceInputTarget) {
        this.occurrenceInputTarget.value = trigger.dataset.occurrenceId || "";
      }
      if (this.hasSubscriptionInputTarget) {
        this.subscriptionInputTarget.value = trigger.dataset.subscriptionId || "";
      }
      if (this.hasDueDateInputTarget) {
        this.dueDateInputTarget.value = trigger.dataset.dueDate || "";
      }
      if (this.hasNameInputTarget) {
        this.nameInputTarget.value = trigger.dataset.subscriptionName || "";
      }
      if (this.hasDateInputTarget) {
        this.dateInputTarget.value = trigger.dataset.dueDate || "";
      }
      if (this.hasAmountInputTarget) {
        this.amountInputTarget.value = trigger.dataset.amount || "";
      }
      if (window.UIkit && this.modalElement) {
        window.UIkit.modal(this.modalElement).show();
      }
    }

    resetForm() {
      if (this.hasPayFormTarget) {
        this.payFormTarget.reset();
      }
      if (this.hasOccurrenceInputTarget) {
        this.occurrenceInputTarget.value = "";
      }
      if (this.hasSubscriptionInputTarget) {
        this.subscriptionInputTarget.value = "";
      }
      if (this.hasDueDateInputTarget) {
        this.dueDateInputTarget.value = "";
      }
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

