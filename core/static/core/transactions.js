import { registerStimulusController, withStimulusModule } from "./stimulus.js";

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
  class TransactionsController extends Controller {
    connect() {
      this.onClick = this.handleClick.bind(this);
      this.onChange = this.handleChange.bind(this);
      this.onAfterSwap = this.handleAfterSwap.bind(this);
      this.onRefresh = this.handleRefresh.bind(this);
      this.onResponseError = this.handleResponseError.bind(this);

      document.body.addEventListener("click", this.onClick);
      document.body.addEventListener("change", this.onChange);
      document.body.addEventListener("htmx:afterSwap", this.onAfterSwap);
      document.body.addEventListener("transactions:refresh", this.onRefresh);
      document.body.addEventListener("htmx:responseError", this.onResponseError);

      this.cacheElements();
      this.applyUIKitFieldClasses(this.element);
      this.initDatePickers(this.element);
      this.syncFilterChipState();

      const autoload = this.element.querySelector("[data-autoload-url]");
      if (autoload && autoload.dataset.autoloadUrl) {
        this.openModal(autoload.dataset.autoloadUrl);
      }
    }

    disconnect() {
      document.body.removeEventListener("click", this.onClick);
      document.body.removeEventListener("change", this.onChange);
      document.body.removeEventListener("htmx:afterSwap", this.onAfterSwap);
      document.body.removeEventListener("transactions:refresh", this.onRefresh);
      document.body.removeEventListener("htmx:responseError", this.onResponseError);
    }

    cacheElements() {
      this.filterForm = this.element.querySelector("#transactions-filters-form");
      this.filterTypeSelect = this.element.querySelector("#id_filter_tx_type");
      this.modal = document.getElementById("transactions-modal");
      this.modalBody = document.getElementById("transactions-modal-body");
    }

    handleClick(event) {
      const modalTrigger = event.target.closest("[data-tx-open-url]");
      if (modalTrigger) {
        event.preventDefault();
        this.openModal(modalTrigger.dataset.txOpenUrl || "");
        return;
      }

      const filterChip = event.target.closest("[data-filter-type]");
      if (filterChip) {
        event.preventDefault();
        if (!this.filterTypeSelect) {
          return;
        }
        this.filterTypeSelect.value = filterChip.dataset.filterType || "";
        this.syncFilterChipState();
        this.submitFilters();
      }
    }

    handleChange(event) {
      const target = event.target;
      if (!target) {
        return;
      }

      if (target.id === "id_filter_tx_type") {
        this.syncFilterChipState();
      }

      if (target.id === "id_tx_type") {
        this.syncTypeSpecificFields();
      }

      if (target.id === "id_source_choice") {
        this.syncSourceField();
      }

      if (target.id === "id_project_choice") {
        this.syncProjectField();
      }

      if (target.id === "id_category_choice") {
        this.syncCategoryField();
      }
    }

    handleAfterSwap(event) {
      const target = event.target;
      if (!target) {
        return;
      }

      this.cacheElements();

      if (target.id === "transactions-modal-body") {
        this.applyUIKitFieldClasses(target);
        this.initDatePickers(target);
        this.syncTypeSpecificFields();
        this.syncSourceField();
        this.syncProjectField();
        this.syncCategoryField();
      }

      if (target.id === "transactions-board") {
        this.syncFilterChipState();
      }
    }

    handleRefresh() {
      this.refreshBoard();
      this.closeModal();
      notify("Transazione aggiornata.", "success");
    }

    handleResponseError() {
      notify("Operazione non riuscita. Riprova.", "danger");
    }

    submitFilters() {
      if (!this.filterForm) {
        return;
      }
      if (typeof this.filterForm.requestSubmit === "function") {
        this.filterForm.requestSubmit();
        return;
      }
      this.filterForm.submit();
    }

    refreshBoard() {
      if (!this.filterForm || !window.htmx) {
        return;
      }

      const endpoint = this.filterForm.getAttribute("hx-get") || this.filterForm.getAttribute("action") || "";
      if (!endpoint) {
        return;
      }

      const params = new URLSearchParams(new FormData(this.filterForm));
      const queryString = params.toString();
      const url = queryString ? `${endpoint}?${queryString}` : endpoint;
      window.htmx.ajax("GET", url, "#transactions-board");
    }

    openModal(url) {
      if (!url || !this.modalBody) {
        return;
      }

      if (window.htmx) {
        window.htmx.ajax("GET", url, "#transactions-modal-body");
      } else {
        window.location.href = url;
        return;
      }

      if (window.UIkit && this.modal) {
        window.UIkit.modal(this.modal).show();
      }
    }

    closeModal() {
      if (!this.modal) {
        return;
      }
      if (window.UIkit) {
        const modal = window.UIkit.modal(this.modal);
        if (modal) {
          modal.hide();
        }
      }
    }

    syncFilterChipState() {
      const selected = this.filterTypeSelect ? this.filterTypeSelect.value : "";
      this.element.querySelectorAll("[data-filter-type]").forEach((chip) => {
        const value = chip.dataset.filterType || "";
        const isActive = value === selected;
        chip.classList.toggle("is-active", isActive);
      });
    }

    syncTypeSpecificFields() {
      if (!this.modalBody) {
        return;
      }

      const typeField = this.modalBody.querySelector("#id_tx_type");
      if (!typeField) {
        return;
      }

      const selectedType = typeField.value || "";
      this.modalBody.querySelectorAll("[data-type-visibility]").forEach((container) => {
        const allowed = (container.dataset.typeVisibility || "")
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean);

        const visible = allowed.length === 0 || allowed.includes(selectedType);
        container.classList.toggle("tx-hidden", !visible);

        container.querySelectorAll("input, select, textarea").forEach((field) => {
          if ((field.getAttribute("type") || "").toLowerCase() === "hidden") {
            return;
          }
          field.disabled = !visible;
        });
      });
    }

    syncSourceField() {
      if (!this.modalBody) {
        return;
      }

      const sourceChoice = this.modalBody.querySelector("#id_source_choice");
      const sourceNameRow = this.modalBody.querySelector("[data-source-new-row]");
      if (!sourceChoice || !sourceNameRow) {
        return;
      }

      const showSourceName = sourceChoice.value === "__new__" && !sourceNameRow.classList.contains("tx-hidden");
      sourceNameRow.classList.toggle("tx-hidden", !showSourceName);

      sourceNameRow.querySelectorAll("input, select, textarea").forEach((field) => {
        if ((field.getAttribute("type") || "").toLowerCase() === "hidden") {
          return;
        }
        field.disabled = !showSourceName;
        if (!showSourceName && field.tagName === "INPUT") {
          field.value = "";
        }
      });
    }

    syncProjectField() {
      if (!this.modalBody) {
        return;
      }

      const projectChoice = this.modalBody.querySelector("#id_project_choice");
      const projectNameRow = this.modalBody.querySelector("[data-project-new-row]");
      if (!projectChoice || !projectNameRow) {
        return;
      }

      const showProjectName = projectChoice.value === "__new__";
      projectNameRow.classList.toggle("tx-hidden", !showProjectName);

      projectNameRow.querySelectorAll("input, select, textarea").forEach((field) => {
        if ((field.getAttribute("type") || "").toLowerCase() === "hidden") {
          return;
        }
        field.disabled = !showProjectName;
        if (!showProjectName && field.tagName === "INPUT") {
          field.value = "";
        }
      });
    }

    syncCategoryField() {
      if (!this.modalBody) {
        return;
      }

      const categoryChoice = this.modalBody.querySelector("#id_category_choice");
      const categoryNameRow = this.modalBody.querySelector("[data-category-new-row]");
      if (!categoryChoice || !categoryNameRow) {
        return;
      }

      const showCategoryName = categoryChoice.value === "__new__";
      categoryNameRow.classList.toggle("tx-hidden", !showCategoryName);

      categoryNameRow.querySelectorAll("input, select, textarea").forEach((field) => {
        if ((field.getAttribute("type") || "").toLowerCase() === "hidden") {
          return;
        }
        field.disabled = !showCategoryName;
        if (!showCategoryName && field.tagName === "INPUT") {
          field.value = "";
        }
      });
    }

    applyUIKitFieldClasses(root) {
      if (!root) {
        return;
      }

      root.querySelectorAll("select").forEach((el) => {
        el.classList.add("uk-select", "uk-form-small");
      });

      root.querySelectorAll("textarea").forEach((el) => {
        el.classList.add("uk-textarea", "uk-form-small");
      });

      root.querySelectorAll("input").forEach((el) => {
        const type = (el.getAttribute("type") || "text").toLowerCase();
        if (["hidden", "checkbox", "radio", "submit", "button"].includes(type)) {
          return;
        }
        if (type === "file") {
          el.classList.add("uk-input", "uk-form-small");
          return;
        }
        el.classList.add("uk-input", "uk-form-small");
      });
    }

    initDatePickers(root) {
      if (!root || !window.flatpickr) {
        return;
      }

      root.querySelectorAll(".date-field").forEach((el) => {
        if (el._flatpickr) {
          return;
        }
        window.flatpickr(el, {
          dateFormat: "Y-m-d",
          allowInput: true,
        });
      });
    }
  }

  registerStimulusController("transactions", TransactionsController);
}).catch(() => {});
