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
