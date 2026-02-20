from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="contacts-dashboard"),
    path("add", views.add_contact, name="contacts-add"),
    path("update", views.update_contact, name="contacts-update"),
    path("remove", views.remove_contact, name="contacts-remove"),
]
