from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="planner-dashboard"),
    path("add", views.add_item, name="planner-add"),
    path("update", views.update_item, name="planner-update"),
    path("remove", views.remove_item, name="planner-remove"),
    # API endpoints (AJAX / HTMX)
    path("api/toggle-status/<int:pk>/", views.api_toggle_status, name="planner-api-toggle"),
    path("api/delete/<int:pk>/", views.api_delete_item, name="planner-api-delete"),
]