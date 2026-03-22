from django.conf import settings

from .models import UserHeroActionsConfig, UserNavConfig
from .navigation import build_site_nav_context


def hero_actions_config(request):
    if not request.user.is_authenticated:
        return {
            "hero_actions_config": {},
            "site_nav": build_site_nav_context(request.path, {}),
        }
    config = UserHeroActionsConfig.objects.filter(user=request.user).first()
    nav_config = UserNavConfig.objects.filter(user=request.user).first()
    return {
        "hero_actions_config": config.config if config else {},
        "site_nav": build_site_nav_context(request.path, nav_config.config if nav_config else {}),
    }


def ui_preferences(request):
    path = request.path or ""
    is_workbench_path = path == "/workbench" or path.startswith("/workbench/")
    return {
        "less_dev_mode": bool(getattr(settings, "LESS_DEV_MODE", False)),
        "ui_use_global_styles": not is_workbench_path,
        "ui_theme": "light",
    }
