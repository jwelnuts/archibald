from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="finance-hub-dashboard"),
    path("vat-codes/", views.vat_codes, name="finance-hub-vat-codes"),

    path("quotes/", views.quotes, name="finance-hub-quotes"),
    path("quotes/add", views.add_quote, name="finance-hub-quotes-add"),
    path("quotes/update", views.update_quote, name="finance-hub-quotes-update"),
    path("quotes/remove", views.remove_quote, name="finance-hub-quotes-remove"),

    path("invoices/", views.invoices, name="finance-hub-invoices"),
    path("invoices/add", views.add_invoice, name="finance-hub-invoices-add"),
    path("invoices/update", views.update_invoice, name="finance-hub-invoices-update"),
    path("invoices/remove", views.remove_invoice, name="finance-hub-invoices-remove"),

    path("work-orders/", views.work_orders, name="finance-hub-work-orders"),
    path("work-orders/add", views.add_work_order, name="finance-hub-work-orders-add"),
    path("work-orders/update", views.update_work_order, name="finance-hub-work-orders-update"),
    path("work-orders/remove", views.remove_work_order, name="finance-hub-work-orders-remove"),
]
