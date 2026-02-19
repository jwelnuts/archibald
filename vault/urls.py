from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="vault-dashboard"),
    path("setup", views.setup_totp, name="vault-setup"),
    path("unlock", views.unlock, name="vault-unlock"),
    path("lock", views.lock, name="vault-lock"),
    path("api/add", views.add_item, name="vault-add"),
    path("api/update", views.update_item, name="vault-update"),
    path("api/remove", views.remove_item, name="vault-remove"),
]
