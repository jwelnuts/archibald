import { registerStimulusController, withStimulusModule } from "./stimulus.js";

withStimulusModule(({ Controller }) => {
  class ProjectsStoryboardController extends Controller {
    static targets = ["filterForm", "noteEditor", "noteForm", "commandInput", "tabNav"];

    connect() {
      this.searchTimer = null;
      this.initializeNoteEditor();
      this.initializeTabs();
    }

    disconnect() {
      if (this.searchTimer) {
        window.clearTimeout(this.searchTimer);
      }
      if (this.noteFormHandler && this.hasNoteFormTarget) {
        this.noteFormTarget.removeEventListener("submit", this.noteFormHandler);
      }
    }

    initializeTabs() {
      if (!this.hasTabNavTarget) return;

      const activeFromServer = this.tabNavTarget.dataset.activeForm;
      if (activeFromServer) {
        const idxMap = { note: 0, task: 1, planner: 2, command: 3 };
        const idx = idxMap[activeFromServer] || 0;

        if (window.UIkit && window.UIkit.tab) {
          const tabEl = this.tabNavTarget.closest("[uk-tab]") || this.tabNavTarget;
          window.UIkit.tab(tabEl).show(idx);
        }
      }
    }

    submitFilters(event) {
      if (event) {
        event.preventDefault();
      }
      if (!this.hasFilterFormTarget || !window.htmx) {
        return;
      }
      window.htmx.trigger(this.filterFormTarget, "submit");
    }

    queueSearch() {
      if (!this.hasFilterFormTarget || !window.htmx) {
        return;
      }
      if (this.searchTimer) {
        window.clearTimeout(this.searchTimer);
      }
      this.searchTimer = window.setTimeout(() => {
        this.submitFilters();
      }, 260);
    }

    setKind(event) {
      event.preventDefault();
      if (!this.hasFilterFormTarget) {
        return;
      }
      const kind = event.currentTarget?.dataset?.kind || "all";
      const kindInput = this.filterFormTarget.querySelector("input[name='kind']");
      if (kindInput) {
        kindInput.value = kind;
      }
      this.submitFilters();
    }

    resetFilters(event) {
      event.preventDefault();
      if (!this.hasFilterFormTarget) {
        return;
      }
      this.filterFormTarget.reset();
      this.submitFilters();
    }

    submitCommand(event) {
      if (event && event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        const form = this.hasCommandInputTarget ? this.commandInputTarget.closest("form") : null;
        if (form) {
          form.submit();
        }
      }
    }

    initializeNoteEditor() {
      if (!this.hasNoteEditorTarget || !this.hasNoteFormTarget || !window.Quill) {
        return;
      }
      const textarea = this.noteFormTarget.querySelector("#id_content");
      const toolbar = this.noteFormTarget.querySelector("#note-editor-toolbar");
      if (!textarea || !toolbar || this.noteEditorTarget.dataset.quillReady === "true") {
        return;
      }

      textarea.required = false;
      const quill = new window.Quill(this.noteEditorTarget, {
        theme: "snow",
        modules: {
          toolbar,
        },
      });

      if (textarea.value) {
        quill.clipboard.dangerouslyPasteHTML(textarea.value);
      }

      this.noteFormHandler = (event) => {
        const html = quill.root.innerHTML.trim();
        const text = quill.getText().trim();
        if (!text) {
          event.preventDefault();
          this.noteEditorTarget.focus();
          return;
        }
        textarea.value = html;
      };

      this.noteFormTarget.addEventListener("submit", this.noteFormHandler);
      this.noteEditorTarget.dataset.quillReady = "true";
    }
  }

  registerStimulusController("projects-storyboard", ProjectsStoryboardController);
});
