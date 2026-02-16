from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='workbench-dashboard'),
    path('api/add', views.add_item, name='workbench-add'),
    path('api/remove', views.remove_item, name='workbench-remove'),
    path('api/update', views.update_item, name='workbench-update'),
    path('debug/logs', views.debug_logs, name='workbench-debug-logs'),
    path('debug/schema', views.db_schema, name='workbench-db-schema'),
]
