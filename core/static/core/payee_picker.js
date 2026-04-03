const DEFAULT_SEARCH_URL = "/contacts/api/payees/search";
const DEFAULT_CREATE_URL = "/contacts/api/payees/quick-create";

let ui = null;
let activePicker = null;
let searchTimer = null;

const escapeHtml = (value) =>
  String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");

const getCsrfToken = () => {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
};

const getInputForPicker = (picker) => {
  if (!picker) return null;
  return picker.querySelector("input[name='payee_name'], input[id*='payee_name']");
};

const getSelectForPicker = (picker) => {
  if (!picker) return null;
  const selectId = picker.dataset.payeeSelectId || "";
  if (!selectId) return null;
  return document.getElementById(selectId);
};

const ensurePickerIsInNewMode = (picker) => {
  const select = getSelectForPicker(picker);
  if (!select) return;
  const hasNewOption = Array.from(select.options || []).some((option) => option.value === "__new__");
  if (!hasNewOption) return;
  if (select.value === "__new__") return;
  select.value = "__new__";
  select.dispatchEvent(new Event("change", { bubbles: true }));
};

const applyPayeeName = (picker, value) => {
  const input = getInputForPicker(picker);
  if (!input) return;
  ensurePickerIsInNewMode(picker);
  input.value = value || "";
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
  input.focus();
};

const searchUrlForPicker = (picker) => picker.dataset.searchUrl || DEFAULT_SEARCH_URL;
const createUrlForPicker = (picker) => picker.dataset.createUrl || DEFAULT_CREATE_URL;

const showModal = (el) => {
  if (!el) return;
  if (window.UIkit && typeof window.UIkit.modal === "function") {
    window.UIkit.modal(el).show();
    return;
  }
  el.hidden = false;
};

const hideModal = (el) => {
  if (!el) return;
  if (window.UIkit && typeof window.UIkit.modal === "function") {
    window.UIkit.modal(el).hide();
    return;
  }
  el.hidden = true;
};

const ensureUi = () => {
  if (ui) return ui;

  const wrapper = document.createElement("div");
  wrapper.innerHTML = `
    <div id="payee-picker-search-modal" uk-modal>
      <div class="uk-modal-dialog uk-modal-body">
        <button class="uk-modal-close-default" type="button" uk-close></button>
        <h3 class="uk-h4 uk-margin-small-bottom">Cerca contatto beneficiario</h3>
        <p class="uk-text-meta uk-margin-small-top">Ricerca rapida per nome, email, telefono o citta.</p>
        <div class="uk-margin-small-top">
          <input id="payee-picker-search-input" class="uk-input" type="text" placeholder="Digita per cercare...">
        </div>
        <div id="payee-picker-search-status" class="uk-text-meta uk-margin-small-top"></div>
        <div id="payee-picker-search-results" class="payee-picker-results uk-margin-small-top"></div>
      </div>
    </div>
    <div id="payee-picker-create-modal" uk-modal>
      <div class="uk-modal-dialog uk-modal-body">
        <button class="uk-modal-close-default" type="button" uk-close></button>
        <h3 class="uk-h4 uk-margin-small-bottom">Nuovo contatto beneficiario</h3>
        <p class="uk-text-meta uk-margin-small-top">Inserisci i dati essenziali e conferma.</p>
        <form id="payee-picker-create-form" class="uk-form-stacked uk-margin-small-top">
          <div class="uk-margin-small">
            <label class="uk-form-label" for="payee-picker-create-name">Nome beneficiario *</label>
            <div class="uk-form-controls">
              <input id="payee-picker-create-name" name="display_name" class="uk-input" type="text" maxlength="160" required>
            </div>
          </div>
          <div class="uk-margin-small">
            <label class="uk-form-label" for="payee-picker-create-email">Email</label>
            <div class="uk-form-controls">
              <input id="payee-picker-create-email" name="email" class="uk-input" type="email" maxlength="254">
            </div>
          </div>
          <div class="uk-margin-small">
            <label class="uk-form-label" for="payee-picker-create-phone">Telefono</label>
            <div class="uk-form-controls">
              <input id="payee-picker-create-phone" name="phone" class="uk-input" type="text" maxlength="40">
            </div>
          </div>
          <div class="uk-margin-small">
            <label class="uk-form-label" for="payee-picker-create-city">Citta</label>
            <div class="uk-form-controls">
              <input id="payee-picker-create-city" name="city" class="uk-input" type="text" maxlength="120">
            </div>
          </div>
          <div id="payee-picker-create-status" class="uk-text-meta uk-margin-small-top"></div>
          <div class="uk-flex uk-flex-wrap uk-grid-small uk-margin-medium-top">
            <button class="uk-button uk-button-primary uk-button-small" type="submit">Salva e usa</button>
            <button class="uk-button uk-button-default uk-button-small" type="button" id="payee-picker-create-cancel">Annulla</button>
          </div>
        </form>
      </div>
    </div>
  `;
  document.body.appendChild(wrapper);

  ui = {
    searchModal: document.getElementById("payee-picker-search-modal"),
    searchInput: document.getElementById("payee-picker-search-input"),
    searchStatus: document.getElementById("payee-picker-search-status"),
    searchResults: document.getElementById("payee-picker-search-results"),
    createModal: document.getElementById("payee-picker-create-modal"),
    createForm: document.getElementById("payee-picker-create-form"),
    createName: document.getElementById("payee-picker-create-name"),
    createEmail: document.getElementById("payee-picker-create-email"),
    createPhone: document.getElementById("payee-picker-create-phone"),
    createCity: document.getElementById("payee-picker-create-city"),
    createStatus: document.getElementById("payee-picker-create-status"),
    createCancel: document.getElementById("payee-picker-create-cancel"),
  };

  ui.searchInput.addEventListener("input", () => {
    if (!activePicker) return;
    if (searchTimer) {
      clearTimeout(searchTimer);
    }
    searchTimer = window.setTimeout(() => {
      runSearch(activePicker, ui.searchInput.value || "");
    }, 220);
  });

  ui.searchResults.addEventListener("click", (event) => {
    const button = event.target.closest("[data-payee-pick]");
    if (!button || !activePicker) return;
    const value = button.getAttribute("data-payee-pick") || "";
    if (!value) return;
    applyPayeeName(activePicker, value);
    hideModal(ui.searchModal);
  });

  ui.createCancel.addEventListener("click", () => {
    hideModal(ui.createModal);
  });

  ui.createForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!activePicker) return;

    const formData = new FormData(ui.createForm);
    const searchUrl = createUrlForPicker(activePicker);

    ui.createStatus.textContent = "Salvataggio in corso...";
    try {
      const response = await fetch(searchUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": getCsrfToken(),
        },
        body: formData,
      });
      const payload = await response.json();
      if (!response.ok || !payload || !payload.contact) {
        ui.createStatus.textContent = (payload && payload.error) || "Errore durante il salvataggio.";
        return;
      }

      applyPayeeName(activePicker, payload.contact.display_name || "");
      ui.createStatus.textContent = payload.created ? "Contatto creato." : "Contatto gia esistente, selezionato.";
      hideModal(ui.createModal);
    } catch (_err) {
      ui.createStatus.textContent = "Errore di rete durante il salvataggio.";
    }
  });

  return ui;
};

const renderSearchResults = (results) => {
  const currentUi = ensureUi();
  if (!results.length) {
    currentUi.searchResults.innerHTML = '<div class="uk-text-meta">Nessun contatto trovato.</div>';
    return;
  }

  currentUi.searchResults.innerHTML = results
    .map((row) => {
      const rawName = row.display_name || "";
      const safeName = escapeHtml(rawName);
      const safePick = escapeHtml(rawName);
      const meta = [row.email, row.phone, row.city].filter(Boolean).join(" · ");
      const safeMeta = escapeHtml(meta || "Contatto rubrica");
      return `
        <article class="payee-picker-result">
          <div class="payee-picker-result-head">
            <strong>${safeName}</strong>
            <button class="uk-button uk-button-primary uk-button-small" type="button" data-payee-pick="${safePick}">Usa</button>
          </div>
          <div class="payee-picker-result-meta">${safeMeta}</div>
        </article>
      `;
    })
    .join("");
};

const runSearch = async (picker, query) => {
  const currentUi = ensureUi();
  const url = searchUrlForPicker(picker);
  const params = new URLSearchParams();
  params.set("q", query || "");
  currentUi.searchStatus.textContent = "Ricerca in corso...";

  try {
    const response = await fetch(`${url}?${params.toString()}`, {
      method: "GET",
      credentials: "same-origin",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
    });
    const payload = await response.json();
    const results = payload && Array.isArray(payload.results) ? payload.results : [];
    renderSearchResults(results);
    currentUi.searchStatus.textContent = `${results.length} risultato/i`;
  } catch (_err) {
    currentUi.searchResults.innerHTML = "";
    currentUi.searchStatus.textContent = "Errore durante la ricerca.";
  }
};

const openSearchModal = (picker) => {
  const currentUi = ensureUi();
  activePicker = picker;
  const input = getInputForPicker(picker);
  const prefill = input ? input.value || "" : "";
  currentUi.searchInput.value = prefill;
  currentUi.searchStatus.textContent = "";
  currentUi.searchResults.innerHTML = "";
  showModal(currentUi.searchModal);
  currentUi.searchInput.focus();
  runSearch(picker, prefill);
};

const openCreateModal = (picker) => {
  const currentUi = ensureUi();
  activePicker = picker;
  const input = getInputForPicker(picker);
  currentUi.createForm.reset();
  currentUi.createStatus.textContent = "";
  currentUi.createName.value = input && input.value ? input.value : "";
  showModal(currentUi.createModal);
  currentUi.createName.focus();
};

const bindPicker = (picker) => {
  if (!picker || picker.dataset.payeePickerBound === "1") return;
  picker.dataset.payeePickerBound = "1";
  picker.addEventListener("click", (event) => {
    const button = event.target.closest("[data-payee-action]");
    if (!button) return;
    event.preventDefault();
    const action = button.getAttribute("data-payee-action");
    if (action === "search") {
      openSearchModal(picker);
      return;
    }
    if (action === "create") {
      openCreateModal(picker);
    }
  });
};

const bindPayeePickers = (root) => {
  if (!root || !root.querySelectorAll) return;
  root.querySelectorAll("[data-payee-picker]").forEach(bindPicker);
};

const initPayeePicker = () => {
  bindPayeePickers(document);
  document.addEventListener("htmx:afterSwap", (event) => {
    bindPayeePickers(event.target || document);
  });
};

export { initPayeePicker };
