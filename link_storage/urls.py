from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="link_storage-dashboard"),
    path("api/add", views.add_item, name="link_storage-add"),
    path("api/update", views.update_item, name="link_storage-update"),
    path("api/remove", views.remove_item, name="link_storage-remove"),
]
