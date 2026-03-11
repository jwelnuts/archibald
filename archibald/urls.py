from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="archibald-dashboard"),
    path("messages", views.messages_api, name="archibald-messages"),
    path("favorite", views.toggle_favorite, name="archibald-favorite"),
    path("insights", views.insights, name="archibald-insights"),
    path("temp/new", views.create_temp_thread, name="archibald-temp-new"),
    path("temp/remove", views.remove_temp_thread, name="archibald-temp-remove"),
    path("quick", views.quick_chat, name="archibald-quick"),
]
