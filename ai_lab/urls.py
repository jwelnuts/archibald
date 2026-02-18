from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="ai-lab-dashboard"),
    path("api/add", views.add_item, name="ai-lab-add"),
    path("api/update", views.update_item, name="ai-lab-update"),
    path("api/remove", views.remove_item, name="ai-lab-remove"),
]
