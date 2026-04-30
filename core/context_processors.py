from pathlib import Path

from django.conf import settings

from .models import UserNavConfig
from .navigation import build_site_nav_context


def site_nav(request):
    """Context processor per la navigazione del sito."""
    if not request.user.is_authenticated:
        return {
            "site_nav": build_site_nav_context(request.path, {}, user=None),
        }
    nav_config = UserNavConfig.objects.filter(user=request.user).first()
    return {
        "site_nav": build_site_nav_context(request.path, nav_config.config if nav_config else {}, user=request.user),
    }


def ui_preferences(request):
    path = request.path or ""
    is_workbench_path = path == "/workbench" or path.startswith("/workbench/")
    styles_css_path = Path(settings.BASE_DIR) / "core" / "static" / "core" / "styles.css"
    style_version = ""
    if getattr(settings, "LESS_DEV_MODE", False):
        try:
            style_version = str(int(styles_css_path.stat().st_mtime))
        except OSError:
            style_version = ""
    return {
        "less_dev_mode": bool(getattr(settings, "LESS_DEV_MODE", False)),
        "ui_style_mode": str(getattr(settings, "UI_STYLE_MODE", "PROD")).upper(),
        "ui_style_version": style_version,
        "ui_use_global_styles": not is_workbench_path,
        "ui_theme": "light",
    }
