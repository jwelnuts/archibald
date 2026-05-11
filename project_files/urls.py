from django.urls import path

from . import views

urlpatterns = [
    path("projects/<int:project_id>/files/", views.file_list, name="project-files-list"),
    path("projects/<int:project_id>/files/upload", views.file_upload, name="project-files-upload"),
    path("projects/<int:project_id>/files/<int:file_id>/delete", views.file_delete, name="project-files-delete"),
    path("projects/<int:project_id>/files/<int:file_id>/download", views.file_download, name="project-files-download"),
]
