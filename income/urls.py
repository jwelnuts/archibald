from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='income-dashboard'),
    path('api/add', views.add_income, name='income-add'),
    path('api/remove', views.remove_income, name='income-remove'),
    path('api/update', views.update_income, name='income-update'),
]
