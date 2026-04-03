from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="contacts-dashboard"),
    path("add", views.add_contact, name="contacts-add"),
    path("update", views.update_contact, name="contacts-update"),
    path("remove", views.remove_contact, name="contacts-remove"),
    path("toolbox", views.toolbox, name="contacts-toolbox"),
    path("price-lists/add", views.add_price_list, name="contacts-price-list-add"),
    path("price-lists/update", views.update_price_list, name="contacts-price-list-update"),
    path("price-lists/remove", views.remove_price_list, name="contacts-price-list-remove"),
    path("api/payees/search", views.api_payee_search, name="contacts-api-payee-search"),
    path("api/payees/quick-create", views.api_payee_quick_create, name="contacts-api-payee-quick-create"),
]
