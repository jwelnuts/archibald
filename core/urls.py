from django.urls import include, path

from . import views

urlpatterns = [
    path("api/mobile/auth/login", views.mobile_auth_login, name="mobile-auth-login"),
    path("api/mobile/auth/refresh", views.mobile_auth_refresh, name="mobile-auth-refresh"),
    path("api/mobile/auth/logout", views.mobile_auth_logout, name="mobile-auth-logout"),
    path("api/mobile/dashboard", views.mobile_dashboard, name="mobile-dashboard"),
    path("api/mobile/routines", views.mobile_routines, name="mobile-routines"),
    path("api/mobile/routines/check", views.mobile_routines_check, name="mobile-routines-check"),
    path("api/mobile/routines/items/create", views.mobile_routines_item_create, name="mobile-routines-item-create"),
    path("api/mobile/routines/items/update", views.mobile_routines_item_update, name="mobile-routines-item-update"),
    path("api/mobile/routines/items/delete", views.mobile_routines_item_delete, name="mobile-routines-item-delete"),
    path('', views.dashboard, name='core-dashboard'),
    path('dashboard/widgets', views.dashboard_widgets, name='core-dashboard-widgets'),
    path('dashboard/preferences', views.dashboard_preferences, name='core-dashboard-preferences'),
    path('dashboard/snapshot', views.dashboard_snapshot, name='core-dashboard-snapshot'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/signup/', views.signup, name='signup'),
    path('profile/', views.profile, name='profile'),
    path('profile/hero-actions/', views.hero_actions, name='hero-actions'),
    path('profile/nav/', views.nav_settings, name='nav-settings'),
    path('calendar/events', views.calendar_events, name='core-calendar-events'),
    path('core/accounts/', views.accounts, name='core-accounts'),
    path('core/accounts/add', views.add_account, name='core-accounts-add'),
    path('core/accounts/remove', views.remove_account, name='core-accounts-remove'),
    path('core/accounts/update', views.update_account, name='core-accounts-update'),
]
