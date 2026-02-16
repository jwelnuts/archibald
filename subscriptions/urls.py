from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='subs-dashboard'),

    path('api/add', views.add_sub, name='subs-add'),
    path('api/remove', views.remove_sub, name='subs-remove'),
    path('api/update', views.update_sub, name='subs-update'),
]
