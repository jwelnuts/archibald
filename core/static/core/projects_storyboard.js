import { registerStimulusController, withStimulusModule } from "./stimulus.js";

withStimulusModule(({ Controller }) => {
  class ProjectsStoryboardController extends Controller {
    static targets = ["filterForm", "kindSelect", "noteEditor", "noteForm"];

    connect() {
      this.searchTimer = null;
      this.initializeNoteEditor();
    }

    disconnect() {
      if (this.searchTimer) {
        window.clearTimeout(this.searchTimer);
      }
      if (this.noteFormHandler && this.hasNoteFormTarget) {
        this.noteFormTarget.removeEventListener("submit", this.noteFormHandler);
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
      if (!this.hasKindSelectTarget) {
        return;
      }
      const kind = event.currentTarget?.dataset?.kind || "all";
      this.kindSelectTarget.value = kind;
      this.submitFilters();
    }

    resetFilters(event) {
      event.preventDefault();
      if (!this.hasFilterFormTarget || !this.hasKindSelectTarget) {
        return;
      }
      this.filterFormTarget.reset();
      this.kindSelectTarget.value = "all";
      this.submitFilters();
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
          window.alert("Inserisci un appunto prima di salvare.");
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
