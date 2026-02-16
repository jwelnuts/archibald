from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='outcome-dashboard'),
    path('api/add', views.add_outcome, name='outcome-add'),
    path('api/remove', views.remove_outcome, name='outcome-remove'),
    path('api/update', views.update_outcome, name='outcome-update'),
]
