from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="todos-dashboard"),
    path("stats", views.stats, name="todos-stats"),
    path("check", views.check_item, name="todos-check"),

    path("lists/add", views.add_list, name="todos-lists-add"),
    path("lists/update", views.update_list, name="todos-lists-update"),
    path("lists/remove", views.remove_list, name="todos-lists-remove"),

    path("items/add", views.add_item, name="todos-items-add"),
    path("items/update", views.update_item, name="todos-items-update"),
    path("items/remove", views.remove_item, name="todos-items-remove"),

    path("api/task/add", views.api_add_task, name="todos-api-task-add"),
    path("api/task/update", views.api_update_task, name="todos-api-task-update"),
    path("api/task/remove", views.api_remove_task, name="todos-api-task-remove"),
    path("api/task/status", views.api_set_task_status, name="todos-api-task-status"),
]
