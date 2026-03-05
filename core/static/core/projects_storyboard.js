import { registerStimulusController, withStimulusModule } from "./stimulus.js";

withStimulusModule(({ Controller }) => {
  class ProjectsStoryboardController extends Controller {
    static targets = ["filterForm", "kindSelect"];

    connect() {
      this.searchTimer = null;
    }

    disconnect() {
      if (this.searchTimer) {
        window.clearTimeout(this.searchTimer);
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
  }

  registerStimulusController("projects-storyboard", ProjectsStoryboardController);
});
