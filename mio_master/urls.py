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
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('core.urls')),
    path('subs/', include('subscriptions.urls')),
    path('income/', include('income.urls')),
    path('outcome/', include('outcome.urls')),
    path('projects/', include('projects.urls')),
    path('todo/', include('todo.urls')),
    path('workbench/', include('workbench.urls')),
    path('transactions/', include('transactions.urls')),
    path('planner/', include('planner.urls')),
    path('routines/', include('routines.urls')),
     path('archibald/', include('archibald.urls')),
    path('ui-generator/', include('ui_generator.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
