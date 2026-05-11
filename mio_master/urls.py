"""
URL configuration for mio_master project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from core import views as core_views
from finance_hub import views as finance_hub_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('media/<path:path>', core_views.protected_media, name='protected-media'),

    path('', include('spa_dashboard.urls')),
    path('', include('core.urls')),
    path('subs/', finance_hub_views.subscriptions_dashboard),
    path('subs/', include('finance_hub.urls')),
    path('projects/', include('projects.urls')),
    # path('todo/', include('todo.urls')),
    path('todos/', include('todos.urls')),
    path('agenda/', include('agenda.urls')),
    path('workbench/', include('workbench.urls')),
    path('transactions/', include('transactions.urls')),
    path('planner/', include('planner.urls')),
    # path('todos/', include('todos.urls')),
    path('archibald/', include('archibald.urls')),
    path('archibald-mail/', include('archibald_mail.urls')),
    path('memory-stock/', include('memory_stock.urls')),
    path('vault/', include('vault.urls')),
    path('finance/', include('finance_hub.urls')),
    path('link_storage/', include('link_storage.urls')),
    path('contacts/', include('contacts.urls')),
    path('', include('social_media.urls')),
    path('', include('project_files.urls')),
]
