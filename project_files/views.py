from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from projects.models import Project
from .models import ProjectFile


@login_required
def file_list(request, project_id):
    user = request.user
    project = get_object_or_404(Project, id=project_id, owner=user)
    files = ProjectFile.objects.filter(owner=user, project=project).order_by("-created_at")
    return render(request, "project_files/file_list.html", {
        "project": project,
        "files": files,
    })


@login_required
@require_http_methods(["POST"])
def file_upload(request, project_id):
    user = request.user
    project = get_object_or_404(Project, id=project_id, owner=user)
    uploaded = request.FILES.get("file")
    name = (request.POST.get("name") or "").strip()
    description = (request.POST.get("description") or "").strip()

    if uploaded:
        ProjectFile.objects.create(
            owner=user,
            project=project,
            file=uploaded,
            name=name or uploaded.name,
            description=description,
        )

    return redirect("project-files-list", project_id=project.id)


@login_required
@require_http_methods(["POST"])
def file_delete(request, project_id, file_id):
    user = request.user
    project = get_object_or_404(Project, id=project_id, owner=user)
    file_obj = get_object_or_404(ProjectFile, id=file_id, owner=user, project=project)
    file_obj.delete()
    return redirect("project-files-list", project_id=project.id)


@login_required
def file_download(request, project_id, file_id):
    user = request.user
    project = get_object_or_404(Project, id=project_id, owner=user)
    file_obj = get_object_or_404(ProjectFile, id=file_id, owner=user, project=project)
    return FileResponse(file_obj.file.open(), as_attachment=True, filename=file_obj.name)
