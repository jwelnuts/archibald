from django.urls import include, path

from . import views

urlpatterns = [
    path('', views.dashboard, name='core-dashboard'),
    path('dashboard/widgets', views.dashboard_widgets, name='core-dashboard-widgets'),
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
