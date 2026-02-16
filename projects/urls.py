from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='projects-dashboard'),
    path('view', views.project_detail, name='projects-detail'),
    path('storyboard', views.project_storyboard, name='projects-storyboard'),
    path('hero-actions', views.project_hero_actions, name='projects-hero-actions'),
    path('api/add', views.add_project, name='projects-add'),
    path('api/remove', views.remove_project, name='projects-remove'),
    path('api/update', views.update_project, name='projects-update'),

    path('categories/', views.categories, name='projects-categories'),
    path('categories/add', views.add_category, name='projects-categories-add'),
    path('categories/remove', views.remove_category, name='projects-categories-remove'),
    path('categories/update', views.update_category, name='projects-categories-update'),

    path('customers/', views.customers, name='projects-customers'),
    path('customers/add', views.add_customer, name='projects-customers-add'),
    path('customers/remove', views.remove_customer, name='projects-customers-remove'),
    path('customers/update', views.update_customer, name='projects-customers-update'),
]
