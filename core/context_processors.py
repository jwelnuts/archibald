from .models import UserHeroActionsConfig


def hero_actions_config(request):
    if not request.user.is_authenticated:
        return {"hero_actions_config": {}}
    config = UserHeroActionsConfig.objects.filter(user=request.user).first()
    return {"hero_actions_config": config.config if config else {}}
