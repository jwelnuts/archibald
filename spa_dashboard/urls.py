from django.urls import path
from . import views

urlpatterns = [
    path("", views.shell, name="spa-dashboard-shell"),
    path("api/spa/layout", views.api_layout_get, name="spa-layout-get"),
    path("api/spa/layout/save", views.api_layout_save, name="spa-layout-save"),
    path("api/spa/widget/<str:widget_id>/data", views.api_widget_data, name="spa-widget-data"),
    path("api/spa/subscriptions/pay", views.api_subscription_pay, name="spa-subs-pay"),
]
