from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="transactions-dashboard"),
    path("partials/board", views.board_partial, name="transactions-board"),
    path("partials/form", views.form_partial, name="transactions-form"),
    path("partials/delete", views.delete_partial, name="transactions-delete"),
]
