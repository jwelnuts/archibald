from django.urls import path

from . import views

urlpatterns = [
    path("projects/<int:project_id>/social/", views.dashboard, name="social-media-dashboard"),
    path("projects/<int:project_id>/social/channel/new", views.channel_create, name="social-media-channel-create"),
    path("projects/<int:project_id>/social/channel/<int:channel_id>/edit", views.channel_edit, name="social-media-channel-edit"),
    path("projects/<int:project_id>/social/channel/<int:channel_id>/toggle", views.channel_toggle, name="social-media-channel-toggle"),
    path("projects/<int:project_id>/social/post/new", views.post_create, name="social-media-post-create"),
    path("projects/<int:project_id>/social/post/<int:post_id>/edit", views.post_edit, name="social-media-post-edit"),
    path("projects/<int:project_id>/social/post/<int:post_id>/status", views.post_status, name="social-media-post-status"),
    path("projects/<int:project_id>/social/post/<int:post_id>/delete", views.post_delete, name="social-media-post-delete"),
]
