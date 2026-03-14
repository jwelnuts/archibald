(function () {
  function hasUkClass(el) {
    return Array.from(el.classList || []).some(function (cls) {
      return cls.indexOf("uk-") === 0;
    });
  }

  function addClasses(el, classes) {
    classes.forEach(function (cls) {
      if (cls && !el.classList.contains(cls)) {
        el.classList.add(cls);
      }
    });
  }

  function asArray(nodeList) {
    return Array.prototype.slice.call(nodeList || []);
  }

  function styleButtons(root) {
    asArray(root.querySelectorAll(".btn")).forEach(function (el) {
      addClasses(el, ["uk-button"]);
      if (el.classList.contains("primary")) {
        addClasses(el, ["uk-button-primary"]);
      } else if (el.classList.contains("danger")) {
        addClasses(el, ["uk-button-danger"]);
      } else {
        addClasses(el, ["uk-button-default"]);
      }
    });

    asArray(
      root.querySelectorAll(
        "button:not(.uk-button), input[type='submit']:not(.uk-button), input[type='button']:not(.uk-button), input[type='reset']:not(.uk-button)"
      )
    ).forEach(function (el) {
      addClasses(el, ["uk-button", "uk-button-default", "uk-button-small"]);
    });
  }

  function styleForms(root) {
    asArray(root.querySelectorAll("form")).forEach(function (form) {
      if (!hasUkClass(form)) {
        addClasses(form, ["uk-form-stacked"]);
      }
    });

    asArray(root.querySelectorAll("label:not(.uk-form-label)")).forEach(function (label) {
      addClasses(label, ["uk-form-label"]);
    });

    asArray(root.querySelectorAll("input, select, textarea")).forEach(function (field) {
      var tag = (field.tagName || "").toLowerCase();
      var type = (field.getAttribute("type") || "").toLowerCase();

      if (tag === "input") {
        if (type === "checkbox") {
          addClasses(field, ["uk-checkbox"]);
          return;
        }
        if (type === "radio") {
          addClasses(field, ["uk-radio"]);
          return;
        }
        if (
          type === "hidden" ||
          type === "submit" ||
          type === "button" ||
          type === "reset" ||
          type === "file" ||
          type === "range" ||
          type === "color"
        ) {
          return;
        }
        addClasses(field, ["uk-input"]);
        return;
      }

      if (tag === "select") {
        addClasses(field, ["uk-select"]);
        return;
      }

      if (tag === "textarea") {
        addClasses(field, ["uk-textarea"]);
      }
    });

    asArray(root.querySelectorAll("form p")).forEach(function (row) {
      if (!hasUkClass(row)) {
        addClasses(row, ["uk-margin-small"]);
      }
    });

    asArray(root.querySelectorAll(".field")).forEach(function (row) {
      if (!hasUkClass(row)) {
        addClasses(row, ["uk-margin-small"]);
      }
    });
  }

  function styleLayout(root) {
    asArray(root.querySelectorAll(".shell, .page")).forEach(function (el) {
      addClasses(el, ["uk-container", "uk-container-large", "uk-margin-top", "uk-margin-bottom"]);
    });

    asArray(root.querySelectorAll("main.content, main.shell")).forEach(function (el) {
      addClasses(el, ["uk-margin"]);
    });

    asArray(root.querySelectorAll(".panel, .card, .profile-card")).forEach(function (el) {
      if (!el.classList.contains("uk-card")) {
        addClasses(el, ["uk-card", "uk-card-default", "uk-card-body", "uk-margin"]);
      }
    });

    asArray(root.querySelectorAll(".narrow")).forEach(function (el) {
      addClasses(el, ["uk-width-1-1", "uk-width-2-3@l", "uk-margin-auto"]);
    });

    asArray(root.querySelectorAll(".grid:not([uk-grid])")).forEach(function (el) {
      addClasses(el, ["uk-grid-small", "uk-child-width-1-1", "uk-child-width-1-2@m"]);
      el.setAttribute("uk-grid", "");
    });

    asArray(root.querySelectorAll(".actions, .top-actions, .top-nav, .shell-nav, .site-nav")).forEach(function (el) {
      addClasses(el, ["uk-flex", "uk-flex-wrap", "uk-flex-middle"]);
    });

    asArray(root.querySelectorAll(".list:not(.uk-list)")).forEach(function (el) {
      addClasses(el, ["uk-list", "uk-list-divider"]);
    });

    asArray(root.querySelectorAll("table:not(.uk-table)")).forEach(function (table) {
      addClasses(table, ["uk-table", "uk-table-small", "uk-table-divider", "uk-table-middle"]);
    });

    asArray(root.querySelectorAll(".warning, .warning-box, .warn")).forEach(function (el) {
      addClasses(el, ["uk-alert", "uk-alert-warning"]);
    });

    asArray(root.querySelectorAll(".info, .note, .flash-item")).forEach(function (el) {
      addClasses(el, ["uk-alert", "uk-alert-primary"]);
    });

    asArray(root.querySelectorAll("footer.site-footer")).forEach(function (el) {
      addClasses(el, ["uk-text-meta", "uk-margin"]);
    });

    asArray(root.querySelectorAll(".muted:not(.uk-text-meta)")).forEach(function (el) {
      addClasses(el, ["uk-text-meta"]);
    });

    asArray(root.querySelectorAll("a.link:not(.uk-link-text)")).forEach(function (el) {
      addClasses(el, ["uk-link-text"]);
    });
  }

  function applyUIKitBaseline(root) {
    styleButtons(root);
    styleForms(root);
    styleLayout(root);
  }

  function run() {
    applyUIKitBaseline(document);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }

  function handleHtmx(event) {
    applyUIKitBaseline(event.target || document);
  }

  document.addEventListener("htmx:afterSwap", handleHtmx);
  document.addEventListener("htmx:afterSettle", handleHtmx);
})();
