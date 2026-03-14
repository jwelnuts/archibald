from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="agenda-dashboard"),
    path("panel", views.panel, name="agenda-panel"),
    path("snapshot", views.snapshot, name="agenda-snapshot"),
    path("item-action", views.item_action, name="agenda-item-action"),
    path("preferences", views.preferences, name="agenda-preferences"),
]
