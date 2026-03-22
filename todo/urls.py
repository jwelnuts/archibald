from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='todo-dashboard'),
    path('api/add', views.add_task, name='todo-add'),
    path('api/remove', views.remove_task, name='todo-remove'),
    path('api/update', views.update_task, name='todo-update'),
    path('api/status', views.set_status, name='todo-set-status'),
    path('api/sync-vtodo', views.sync_vtodo, name='todo-sync-vtodo'),
]
