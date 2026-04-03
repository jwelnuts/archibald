from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='projects-dashboard'),
    path('view', views.project_detail, name='projects-detail'),
    path('quotes/add', views.add_project_quote, name='projects-quote-add'),
    path('subprojects/add', views.add_subproject, name='projects-subproject-add'),
    path('subprojects/view', views.subproject_detail, name='projects-subproject-detail'),
    path('subprojects/update', views.update_subproject, name='projects-subproject-update'),
    path('storyboard', views.project_storyboard, name='projects-storyboard'),
    path('storyboard/log', views.project_storyboard_log, name='projects-storyboard-log'),
    path('storyboard/note/delete', views.project_storyboard_delete_note, name='projects-storyboard-delete-note'),
    path('hero-actions', views.project_hero_actions, name='projects-hero-actions'),
    path('api/add', views.add_project, name='projects-add'),
    path('api/remove', views.remove_project, name='projects-remove'),
    path('api/update', views.update_project, name='projects-update'),

    path('categories/', views.categories, name='projects-categories'),
    path('categories/add', views.add_category, name='projects-categories-add'),
    path('categories/remove', views.remove_category, name='projects-categories-remove'),
    path('categories/update', views.update_category, name='projects-categories-update'),
]
