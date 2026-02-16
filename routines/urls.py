from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="routines-dashboard"),
    path("check", views.check_item, name="routines-check"),

    path("api/add", views.add_routine, name="routines-add"),
    path("api/update", views.update_routine, name="routines-update"),
    path("api/remove", views.remove_routine, name="routines-remove"),

    path("items/add", views.add_item, name="routines-items-add"),
    path("items/update", views.update_item, name="routines-items-update"),
    path("items/remove", views.remove_item, name="routines-items-remove"),
]
