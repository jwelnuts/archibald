import { registerStimulusController, withStimulusModule } from "./stimulus.js";

withStimulusModule(({ Controller }) => {
  class TodoController extends Controller {
    connect() {
      this.todayDate = this.getTodayDate();
      this.flatpickrInstances = [];
      this.projectChoice = this.element.querySelector("#id_project_choice");
      this.projectNameRow = this.element.querySelector("[data-project-name-row]");
      this.projectNameInput = this.element.querySelector("#id_project_name");
      this.categoryChoice = this.element.querySelector("#id_category_choice");
      this.categoryNameRow = this.element.querySelector("[data-category-name-row]");
      this.categoryNameInput = this.element.querySelector("#id_category_name");
      this.filterButtons = this.element.querySelectorAll("[data-todo-filter]");
      this.activeFilter = "all";

      this.onChange = this.handleChange.bind(this);
      this.onClick = this.handleClick.bind(this);
      this.onAfterSettle = this.handleAfterSettle.bind(this);
      this.onResponseError = this.handleResponseError.bind(this);
      this.element.addEventListener("change", this.onChange);
      this.element.addEventListener("click", this.onClick);
      document.body.addEventListener("htmx:afterSettle", this.onAfterSettle);
      document.body.addEventListener("htmx:responseError", this.onResponseError);

      this.applyUIKitFieldClasses();
      this.initDatePickers();
      this.syncProjectFieldVisibility();
      this.syncCategoryFieldVisibility();
      this.refreshTaskRows();
      this.setFilter(this.activeFilter);
    }

    disconnect() {
      this.element.removeEventListener("change", this.onChange);
      this.element.removeEventListener("click", this.onClick);
      document.body.removeEventListener("htmx:afterSettle", this.onAfterSettle);
      document.body.removeEventListener("htmx:responseError", this.onResponseError);
      this.flatpickrInstances.forEach((instance) => {
        if (instance && typeof instance.destroy === "function") {
          instance.destroy();
        }
      });
      this.flatpickrInstances = [];
    }

    handleChange(event) {
      if (event.target && event.target.id === "id_project_choice") {
        this.syncProjectFieldVisibility();
      }
      if (event.target && event.target.id === "id_category_choice") {
        this.syncCategoryFieldVisibility();
      }
    }

    handleClick(event) {
      const button = event.target.closest("[data-todo-filter]");
      if (!button) {
        return;
      }
      event.preventDefault();
      this.setFilter(button.dataset.todoFilter || "all");
    }

    handleAfterSettle() {
      this.refreshTaskRows();
      this.applyFilters();
    }

    handleResponseError() {
      if (window.UIkit && typeof window.UIkit.notification === "function") {
        window.UIkit.notification({
          message: "Aggiornamento non riuscito. Riprova.",
          status: "danger",
          pos: "bottom-center",
          timeout: 2200,
        });
      }
    }

    getTodayDate() {
      const now = new Date();
      const month = String(now.getMonth() + 1).padStart(2, "0");
      const day = String(now.getDate()).padStart(2, "0");
      return `${now.getFullYear()}-${month}-${day}`;
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
        const instance = window.flatpickr(el, {
          dateFormat: "Y-m-d",
          allowInput: true,
        });
        this.flatpickrInstances.push(instance);
      });
    }

    syncProjectFieldVisibility() {
      if (!this.projectChoice || !this.projectNameRow || !this.projectNameInput) {
        return;
      }
      const useNewProject = this.projectChoice.value === "__new__";
      this.projectNameRow.classList.toggle("todo-hidden", !useNewProject);
      this.projectNameInput.disabled = !useNewProject;
      if (!useNewProject) {
        this.projectNameInput.value = "";
      }
    }

    syncCategoryFieldVisibility() {
      if (!this.categoryChoice || !this.categoryNameRow || !this.categoryNameInput) {
        return;
      }
      const useNewCategory = this.categoryChoice.value === "__new__";
      this.categoryNameRow.classList.toggle("todo-hidden", !useNewCategory);
      this.categoryNameInput.disabled = !useNewCategory;
      if (!useNewCategory) {
        this.categoryNameInput.value = "";
      }
    }

    taskRows() {
      return Array.from(this.element.querySelectorAll("[data-todo-task-row]"));
    }

    refreshTaskRows() {
      this.taskRows().forEach((row) => {
        const status = (row.dataset.status || "").toUpperCase();
        const dueDate = row.dataset.dueDate || "";
        const isOverdue = Boolean(dueDate) && dueDate < this.todayDate && status !== "DONE";

        row.classList.remove("is-open", "is-in-progress", "is-done", "is-overdue");
        if (status === "DONE") {
          row.classList.add("is-done");
        } else if (status === "IN_PROGRESS") {
          row.classList.add("is-in-progress");
        } else {
          row.classList.add("is-open");
        }
        if (isOverdue) {
          row.classList.add("is-overdue");
        }
      });
    }

    setFilter(value) {
      this.activeFilter = value;
      this.filterButtons.forEach((button) => {
        button.classList.toggle("is-active", button.dataset.todoFilter === value);
      });
      this.applyFilters();
    }

    applyFilters() {
      this.taskRows().forEach((row) => {
        const status = (row.dataset.status || "").toUpperCase();
        const dueDate = row.dataset.dueDate || "";
        const isOverdue = Boolean(dueDate) && dueDate < this.todayDate && status !== "DONE";
        const isToday = dueDate === this.todayDate && status !== "DONE";

        let visible = true;
        if (this.activeFilter === "open") {
          visible = status === "OPEN";
        } else if (this.activeFilter === "in_progress") {
          visible = status === "IN_PROGRESS";
        } else if (this.activeFilter === "done") {
          visible = status === "DONE";
        } else if (this.activeFilter === "today") {
          visible = isToday;
        } else if (this.activeFilter === "overdue") {
          visible = isOverdue;
        }
        row.classList.toggle("todo-hidden", !visible);
      });
    }
  }

  registerStimulusController("todo", TodoController);
}).catch(() => {});
