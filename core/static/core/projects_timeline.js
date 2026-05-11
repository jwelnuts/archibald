import { registerStimulusController } from "./stimulus.js";

registerStimulusController("timeline", class extends window.StimulusModule.Controller {
  static targets = ["weekSelect"];

  static values = {
    weekStart: String,
  };

  connect() {
    this.currentWeek = this.weekStartValue || this._currentWeekStart();
  }

  prevWeek() {
    const d = new Date(this.currentWeek);
    d.setDate(d.getDate() - 7);
    this._navigate(d);
  }

  nextWeek() {
    const d = new Date(this.currentWeek);
    d.setDate(d.getDate() + 7);
    this._navigate(d);
  }

  weekChanged() {
    const val = this.weekSelectTarget.value;
    if (!val) return;
    this._navigate(new Date(val));
  }

  _navigate(weekStart) {
    this.currentWeek = weekStart.toISOString().split("T")[0];
    const url = new URL(window.location.href);
    url.searchParams.set("week", this.currentWeek);
    // Preserve scope param
    const scope = url.searchParams.get("scope") || "active";
    url.searchParams.set("scope", scope);
    window.location.href = url.toString();
  }

  _currentWeekStart() {
    const today = new Date();
    const day = today.getDay();
    const monday = new Date(today);
    monday.setDate(today.getDate() - ((day + 6) % 7));
    return monday.toISOString().split("T")[0];
  }
});