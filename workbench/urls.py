from functools import wraps

from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import path

from . import views


def superuser_only(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/accounts/login/?next={request.get_full_path()}")
        if not request.user.is_superuser:
            return HttpResponseForbidden("Workbench disponibile solo per superuser.")
        return view_func(request, *args, **kwargs)

    return _wrapped


urlpatterns = [
    path('', superuser_only(views.dashboard), name='workbench-dashboard'),
    path('api/add', superuser_only(views.add_item), name='workbench-add'),
    path('api/remove', superuser_only(views.remove_item), name='workbench-remove'),
    path('api/update', superuser_only(views.update_item), name='workbench-update'),
    path('debug/logs', superuser_only(views.debug_logs), name='workbench-debug-logs'),
    path('debug/radicale', superuser_only(views.radicale_debug), name='workbench-debug-radicale'),
    path('debug/api-endpoints', superuser_only(views.api_endpoints), name='workbench-api-endpoints'),
    path('debug/schema', superuser_only(views.db_schema), name='workbench-db-schema'),
]
