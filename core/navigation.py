import json


DEFAULT_APP_OPTIONS = [
    {"key": "subscriptions", "label": "Subscriptions", "url": "/subs/", "icon": "credit-card"},
    {"key": "finance_hub", "label": "Finance Hub", "url": "/finance/", "icon": "database"},
    {"key": "contacts", "label": "Contacts", "url": "/contacts/", "icon": "users"},
    {"key": "transactions", "label": "Transactions", "url": "/transactions/", "icon": "sorting"},
    {"key": "projects", "label": "Projects", "url": "/projects/", "icon": "folder"},
    {"key": "categories", "label": "Categories", "url": "/projects/categories/", "icon": "tag"},
    {"key": "todo", "label": "Todo", "url": "/todo/", "icon": "check"},
    {"key": "planner", "label": "Planner", "url": "/planner/", "icon": "table"},
    {"key": "agenda", "label": "Agenda", "url": "/agenda/", "icon": "calendar"},
    {"key": "routines", "label": "Routines", "url": "/routines/", "icon": "clock"},
    {"key": "archibald", "label": "Archibald", "url": "/archibald/", "icon": "commenting"},
    {"key": "archibald_mail", "label": "Archibald Mail", "url": "/archibald-mail/", "icon": "mail"},
    {"key": "ai_lab", "label": "AI Lab", "url": "/ai-lab/", "icon": "bolt"},
    {"key": "personal_lab", "label": "Personal Lab", "url": "/ai-lab/personal-lab/", "icon": "code"},
    {"key": "vault", "label": "Vault", "url": "/vault/", "icon": "lock"},
    {"key": "workbench", "label": "Workbench", "url": "/workbench/", "icon": "cog"},
    {"key": "accounts", "label": "Accounts", "url": "/core/accounts/", "icon": "settings"},
    {"key": "profile", "label": "Profilo", "url": "/profile/", "icon": "user"},
]

APP_OPTION_BY_KEY = {item["key"]: item for item in DEFAULT_APP_OPTIONS}
DEFAULT_APP_ORDER = [item["key"] for item in DEFAULT_APP_OPTIONS]
MAX_CUSTOM_LINKS = 6
MAX_WIDGETS = 12


def _is_valid_custom_url(value: str):
    return value.startswith("/") or value.startswith("http://") or value.startswith("https://")


def _sanitize_custom_links(raw_links):
    if not isinstance(raw_links, list):
        return []
    cleaned = []
    for row in raw_links:
        if not isinstance(row, dict):
            continue
        label = (str(row.get("label") or "")).strip()
        url = (str(row.get("url") or "")).strip()
        if not label or not url or not _is_valid_custom_url(url):
            continue
        cleaned.append(
            {
                "label": label[:40],
                "url": url[:300],
                "external": url.startswith("http://") or url.startswith("https://"),
            }
        )
        if len(cleaned) >= MAX_CUSTOM_LINKS:
            break
    return cleaned


def _sanitize_widgets(raw_widgets):
    if not isinstance(raw_widgets, list):
        return []
    cleaned = []
    for row in raw_widgets:
        if not isinstance(row, dict):
            continue
        title = (str(row.get("title") or "")).strip()
        widget_type = (str(row.get("type") or "text")).strip().lower()
        config = row.get("config")
        if not isinstance(config, dict):
            config = {}
        if not title:
            continue
        cleaned.append(
            {
                "title": title[:80],
                "type": widget_type[:24],
                "config": config,
            }
        )
        if len(cleaned) >= MAX_WIDGETS:
            break
    return cleaned


def normalize_nav_config(raw_config):
    if not isinstance(raw_config, dict):
        raw_config = {}

    order = [key for key in raw_config.get("app_order", []) if key in APP_OPTION_BY_KEY]
    for key in DEFAULT_APP_ORDER:
        if key not in order:
            order.append(key)

    hidden_apps = {key for key in raw_config.get("hidden_apps", []) if key in APP_OPTION_BY_KEY}
    app_options = [APP_OPTION_BY_KEY[key] for key in order if key not in hidden_apps]
    custom_links = _sanitize_custom_links(raw_config.get("custom_links", []))
    widgets = _sanitize_widgets(raw_config.get("widgets", []))

    return {
        "_configured": bool(raw_config.get("_configured")),
        "app_order": order,
        "hidden_apps": sorted(hidden_apps),
        "custom_links": custom_links,
        "widgets": widgets,
        "app_options": app_options,
    }


def selected_app_key_for_path(path: str, app_options):
    best_key = ""
    best_len = 0
    for item in app_options:
        url = item["url"]
        if path.startswith(url) and len(url) > best_len:
            best_key = item["key"]
            best_len = len(url)
    return best_key


def build_site_nav_context(path: str, raw_config):
    normalized = normalize_nav_config(raw_config)
    selected_key = selected_app_key_for_path(path or "", DEFAULT_APP_OPTIONS)
    selected_app = APP_OPTION_BY_KEY.get(selected_key)
    return {
        "app_options": normalized["app_options"],
        "selected_app_key": selected_key,
        "selected_app": selected_app,
        "custom_links": normalized["custom_links"],
        # Foundation for future personal widgets. For now we only store/preview this config.
        "widgets": normalized["widgets"],
    }


def parse_widgets_json(value: str):
    raw = (value or "").strip()
    if not raw:
        return []
    parsed = json.loads(raw)
    if not isinstance(parsed, list):
        raise ValueError("Il JSON widgets deve essere una lista.")
    return _sanitize_widgets(parsed)
