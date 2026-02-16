from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="archibald-dashboard"),
    path("messages", views.messages_api, name="archibald-messages"),
    path("favorite", views.toggle_favorite, name="archibald-favorite"),
    path("insights", views.insights, name="archibald-insights"),
    path("quick", views.quick_chat, name="archibald-quick"),
]
