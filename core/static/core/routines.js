const modal = document.getElementById("routine-modal");

if (modal) {
  const modalTitle = document.getElementById("routine-modal-title");
  const modalFields = document.getElementById("routine-modal-fields");
  const modalItem = document.getElementById("routine-modal-item");
  const modalWeek = document.getElementById("routine-modal-week");

  const closeModal = () => {
    modal.setAttribute("hidden", "");
    document.body.classList.remove("modal-open");
  };

  const openModal = (button) => {
    const itemId = button.getAttribute("data-item-id") || "";
    const week = button.getAttribute("data-week") || "";
    const title = button.getAttribute("data-title") || "Routine";
    const schemaId = button.getAttribute("data-schema-id") || "";
    const dataId = button.getAttribute("data-data-id") || "";

    modalItem.value = itemId;
    modalWeek.value = week;
    modalTitle.textContent = `Completa: ${title}`;

    let schema = [];
    let data = {};
    const schemaEl = schemaId ? document.getElementById(schemaId) : null;
    const dataEl = dataId ? document.getElementById(dataId) : null;

    if (schemaEl) {
      try {
        schema = JSON.parse(schemaEl.textContent);
      } catch (err) {
        schema = [];
      }
    }

    if (dataEl) {
      try {
        data = JSON.parse(dataEl.textContent) || {};
      } catch (err) {
        data = {};
      }
    }

    modalFields.innerHTML = "";

    if (!Array.isArray(schema) || schema.length === 0) {
      const empty = document.createElement("div");
      empty.className = "note";
      empty.textContent = "Nessun campo personalizzato per questa routine.";
      modalFields.appendChild(empty);
    } else {
      schema.forEach((field) => {
        const wrapper = document.createElement("div");
        wrapper.className = "field";

        const label = document.createElement("label");
        label.textContent = field.label || field.name || "Campo";

        const fieldName = field.name || "custom";
        const inputId = `modal_${itemId}_${fieldName}`;
        label.setAttribute("for", inputId);

        let input;
        const value = data[fieldName];

        if (field.type === "textarea") {
          input = document.createElement("textarea");
          input.rows = 3;
          input.value = value || "";
        } else if (field.type === "select") {
          input = document.createElement("select");
          const placeholder = document.createElement("option");
          placeholder.value = "";
          placeholder.textContent = "Seleziona...";
          input.appendChild(placeholder);
          const options = Array.isArray(field.options) ? field.options : [];
          options.forEach((option) => {
            const opt = document.createElement("option");
            if (Array.isArray(option)) {
              opt.value = option[0];
              opt.textContent = option[1];
            } else if (option && typeof option === "object") {
              opt.value = option.value || option.id || option.label || "";
              opt.textContent = option.label || option.value || option.id || "";
            } else {
              opt.value = option;
              opt.textContent = option;
            }
            if (value !== undefined && String(value) === String(opt.value)) {
              opt.selected = true;
            }
            input.appendChild(opt);
          });
        } else {
          input = document.createElement("input");
          if (["number", "time", "date", "checkbox"].includes(field.type)) {
            input.type = field.type;
          } else {
            input.type = "text";
          }

          if (input.type === "checkbox") {
            input.checked = Boolean(value);
          } else if (value !== undefined && value !== null) {
            input.value = value;
          }
        }

        input.id = inputId;
        input.name = `data_${fieldName}`;
        if (field.placeholder) {
          input.placeholder = field.placeholder;
        }
        if (field.required) {
          input.required = true;
        }

        wrapper.appendChild(label);
        wrapper.appendChild(input);
        modalFields.appendChild(wrapper);
      });
    }

    modal.removeAttribute("hidden");
    document.body.classList.add("modal-open");
  };

  document.querySelectorAll(".routine-done-btn").forEach((button) => {
    button.addEventListener("click", () => openModal(button));
  });

  modal.querySelectorAll("[data-modal-close]").forEach((btn) => {
    btn.addEventListener("click", closeModal);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hasAttribute("hidden")) {
      closeModal();
    }
  });
}
