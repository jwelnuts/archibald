import { registerStimulusController, withStimulusModule } from "./stimulus.js";

withStimulusModule(({ Controller }) => {
  class ProjectsTimelineController extends Controller {
    static targets = ["canvas", "svg"];

    connect() {
      this.dayWidth = 24;
      this.minDayWidth = 8;
      this.maxDayWidth = 80;
      this.barHeight = 24;
      this.groupGap = 14;
      this.barGap = 3;
      this.headerHeight = 38;
      this.labelWidth = 200;
      this.scrollLeft = 0;

      const scriptTag = document.getElementById("timeline-data");
      if (scriptTag) {
        try {
          this.timelineData = JSON.parse(scriptTag.textContent);
          this.render();
        } catch (e) {
          console.error("Timeline: failed to parse data", e);
        }
      }

      window.addEventListener("resize", () => this.render());
    }

    zoomIn() {
      this.dayWidth = Math.min(this.maxDayWidth, this.dayWidth * 1.4);
      this.render();
    }

    zoomOut() {
      this.dayWidth = Math.max(this.minDayWidth, this.dayWidth / 1.4);
      this.render();
    }

    scrollToToday() {
      if (!this.timelineData || !this.timelineData.today) return;
      const today = new Date(this.timelineData.today);
      const start = new Date(this.timelineData.range_start);
      const diffDays = Math.floor((today - start) / (1000 * 60 * 60 * 24));
      const scrollX = diffDays * this.dayWidth - 100;
      this.canvasTarget.scrollLeft = Math.max(0, scrollX);
    }

    render() {
      const data = this.timelineData;
      if (!data || !data.projects || !this.hasSvgTarget) return;

      const today = new Date(data.today);
      const rangeStart = new Date(data.range_start);
      const rangeEnd = new Date(data.range_end);
      const totalDays = Math.ceil((rangeEnd - rangeStart) / (1000 * 60 * 60 * 24)) + 1;

      let totalRows = 0;
      for (const proj of data.projects) {
        totalRows += 1;
        totalRows += proj.bars.length;
      }

      const svgWidth = Math.max(this.labelWidth + totalDays * this.dayWidth + 40, this.canvasTarget?.clientWidth || 800);
      const svgHeight = totalRows * (this.barHeight + this.barGap) + data.projects.length * this.groupGap + this.headerHeight + 20;

      let svg = this.svgTarget;
      svg.setAttribute("width", svgWidth);
      svg.setAttribute("height", svgHeight);
      svg.setAttribute("viewBox", `0 0 ${svgWidth} ${svgHeight}`);

      let html = "";

      const dayMs = 1000 * 60 * 60 * 24;
      const todayTime = today.getTime();

      for (let d = 0; d < totalDays; d++) {
        const cellTs = rangeStart.getTime() + d * dayMs;
        const cellDate = new Date(cellTs);
        const x = this.labelWidth + d * this.dayWidth;
        const isToday = cellDate.toDateString() === today.toDateString();
        const isWeekend = cellDate.getDay() === 0 || cellDate.getDay() === 6;

        html += `<rect x="${x}" y="${this.headerHeight}" width="${this.dayWidth}" height="${svgHeight - this.headerHeight}" fill="${isToday ? "#1e3a5f" : isWeekend ? "#0f172a" : "#020617"}" />`;

        if (this.dayWidth > 14 || isToday || d % 7 === 0) {
          html += `<line x1="${x}" y1="${this.headerHeight}" x2="${x}" y2="${svgHeight}" stroke="#1e293b" stroke-width="1" />`;
        }
      }

      html += `<rect x="0" y="0" width="${svgWidth}" height="${this.headerHeight}" fill="#0f172a" />`;
      html += `<line x1="0" y1="${this.headerHeight}" x2="${svgWidth}" y2="${this.headerHeight}" stroke="#334155" stroke-width="1" />`;

      const labelInterval = Math.max(1, Math.floor(14 / this.dayWidth) || 1);
      for (let d = 0; d < totalDays; d += labelInterval) {
        const cellDate = new Date(rangeStart.getTime() + d * dayMs);
        const x = this.labelWidth + d * this.dayWidth;
        const label = cellDate.toLocaleDateString("it-IT", { day: "numeric", month: "short" });
        html += `<text x="${x + 4}" y="22" fill="#94a3b8" font-size="11" font-family="Space Grotesk, sans-serif">${label}</text>`;
      }

      html += `<text x="8" y="22" fill="#94a3b8" font-size="11" font-family="Space Grotesk, sans-serif">PROGETTO / ELEMENTO</text>`;

      let y = this.headerHeight + 6;
      const todayOffset = Math.floor((todayTime - rangeStart.getTime()) / dayMs);
      const todayX = this.labelWidth + todayOffset * this.dayWidth + this.dayWidth / 2;

      for (const proj of data.projects) {
        const projY = y;

        html += `<rect x="0" y="${projY}" width="${svgWidth}" height="${this.barHeight}" fill="#0f172a" rx="4" />`;
        html += `<text x="10" y="${projY + this.barHeight - 7}" fill="#f8fafc" font-size="13" font-weight="700" font-family="Space Grotesk, sans-serif">${this._esc(proj.title)}</text>`;
        html += `<text x="${this.labelWidth - 14}" y="${projY + this.barHeight - 7}" fill="#64748b" font-size="11" font-family="Space Grotesk, sans-serif" text-anchor="end">${proj.bars_count} elementi</text>`;

        y += this.barHeight + this.barGap;

        for (const bar of proj.bars) {
          const barStart = new Date(bar.start);
          const barEnd = new Date(bar.end);
          const startX = this.labelWidth + (Math.floor((barStart.getTime() - rangeStart.getTime()) / dayMs)) * this.dayWidth;
          const duration = Math.max(1, Math.ceil((barEnd.getTime() - barStart.getTime()) / dayMs));
          const barWidth = Math.max(4, duration * this.dayWidth);
          const barY = y;
          const radius = 4;

          html += `<a href="${bar.url}" target="_self">`;
          html += `<rect x="${startX}" y="${barY}" width="${barWidth}" height="${this.barHeight}" fill="${bar.color}" rx="${radius}" opacity="0.85">`;
          html += `<title>${this._esc(bar.title)} | ${bar.status} | ${bar.progress}%</title>`;
          html += `</rect>`;

          if (bar.progress > 0 && bar.progress < 100) {
            const progressW = barWidth * (bar.progress / 100);
            html += `<rect x="${startX}" y="${barY}" width="${progressW}" height="${this.barHeight}" fill="${bar.color}" rx="${radius}" opacity="1" />`;
          }

          if (barWidth > 50) {
            html += `<text x="${startX + 6}" y="${barY + this.barHeight - 8}" fill="#fff" font-size="11" font-weight="600" font-family="Space Grotesk, sans-serif">${this._esc(bar.title)}</text>`;
          }

          html += `</a>`;

          y += this.barHeight + this.barGap;
        }

        y += this.groupGap - this.barGap;
      }

      html += `<line x1="${todayX}" y1="${this.headerHeight}" x2="${todayX}" y2="${svgHeight}" stroke="#22c55e" stroke-width="2" stroke-dasharray="6 3" />`;
      html += `<rect x="${todayX - 18}" y="4" width="36" height="18" fill="#22c55e" rx="4" />`;
      html += `<text x="${todayX}" y="16" fill="#fff" font-size="10" font-weight="700" font-family="Space Grotesk, sans-serif" text-anchor="middle">OGGI</text>`;

      svg.innerHTML = html;

      if (this.scrollLeft) {
        this.canvasTarget.scrollLeft = this.scrollLeft;
      }
    }

    _esc(str) {
      if (!str) return "";
      return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }
  }

  registerStimulusController("projects-timeline", ProjectsTimelineController);
});
