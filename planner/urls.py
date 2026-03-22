from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="planner-dashboard"),
    path("add", views.add_item, name="planner-add"),
    path("update", views.update_item, name="planner-update"),
    path("remove", views.remove_item, name="planner-remove"),
]
