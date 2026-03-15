from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="memory-stock-dashboard"),
    path("api/add", views.add_item, name="memory-stock-add"),
    path("api/update", views.update_item, name="memory-stock-update"),
    path("api/remove", views.remove_item, name="memory-stock-remove"),
    path("api/archive", views.toggle_archive, name="memory-stock-archive"),
]
