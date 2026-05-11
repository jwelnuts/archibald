from django.contrib import admin

from .models import ProjectFile


@admin.register(ProjectFile)
class ProjectFileAdmin(admin.ModelAdmin):
    list_display = ["name", "project", "owner", "created_at"]
    list_filter = ["project"]
    search_fields = ["name", "description"]
