from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='workbench-dashboard'),
    path('api/cleanup-generated-app', views.cleanup_generated_app_action, name='workbench-cleanup-generated-app'),
    path('api/add', views.add_item, name='workbench-add'),
    path('api/remove', views.remove_item, name='workbench-remove'),
    path('api/update', views.update_item, name='workbench-update'),
    path('ai/ui-generator', views.ai_ui_generator, name='workbench-ai-ui-generator'),
    path('ai/app-generator', views.ai_app_generator, name='workbench-ai-app-generator'),
    path('debug/logs', views.debug_logs, name='workbench-debug-logs'),
    path('debug/radicale', views.radicale_debug, name='workbench-debug-radicale'),
    path('debug/api-endpoints', views.api_endpoints, name='workbench-api-endpoints'),
    path('debug/schema', views.db_schema, name='workbench-db-schema'),
]
