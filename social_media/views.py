from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from projects.models import Project
from .forms import SocialChannelForm, SocialPostForm
from .models import SocialChannel, SocialPost


@login_required
def dashboard(request, project_id):
    user = request.user
    project = get_object_or_404(Project, id=project_id, owner=user)
    if not project.is_module_enabled("social_media"):
        return redirect("/projects/")

    channels = (
        SocialChannel.objects.filter(owner=user, project=project)
        .order_by("platform", "name")
    )
    posts = (
        SocialPost.objects.filter(owner=user, project=project)
        .select_related("channel")
        .order_by("-scheduled_at", "-created_at")[:20]
    )

    context = {
        "project": project,
        "channels": channels,
        "posts": posts,
    }
    return render(request, "social_media/dashboard.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def channel_create(request, project_id):
    user = request.user
    project = get_object_or_404(Project, id=project_id, owner=user)
    if not project.is_module_enabled("social_media"):
        return redirect("/projects/")

    if request.method == "POST":
        form = SocialChannelForm(request.POST, owner=user, project=project)
        if form.is_valid():
            form.save()
            return redirect("social-media-dashboard", project_id=project.id)
    else:
        form = SocialChannelForm(owner=user, project=project)

    return render(request, "social_media/channel_form.html", {
        "project": project,
        "form": form,
        "title": "Nuovo canale",
    })


@login_required
@require_http_methods(["GET", "POST"])
def channel_edit(request, project_id, channel_id):
    user = request.user
    project = get_object_or_404(Project, id=project_id, owner=user)
    channel = get_object_or_404(SocialChannel, id=channel_id, owner=user, project=project)

    if request.method == "POST":
        form = SocialChannelForm(request.POST, instance=channel, owner=user, project=project)
        if form.is_valid():
            form.save()
            return redirect("social-media-dashboard", project_id=project.id)
    else:
        form = SocialChannelForm(instance=channel, owner=user, project=project)

    return render(request, "social_media/channel_form.html", {
        "project": project,
        "form": form,
        "channel": channel,
        "title": "Modifica canale",
    })


@login_required
@require_http_methods(["POST"])
def channel_toggle(request, project_id, channel_id):
    user = request.user
    project = get_object_or_404(Project, id=project_id, owner=user)
    channel = get_object_or_404(SocialChannel, id=channel_id, owner=user, project=project)
    channel.is_active = not channel.is_active
    channel.save(update_fields=["is_active", "updated_at"])
    return redirect("social-media-dashboard", project_id=project.id)


@login_required
@require_http_methods(["GET", "POST"])
def post_create(request, project_id):
    user = request.user
    project = get_object_or_404(Project, id=project_id, owner=user)
    if not project.is_module_enabled("social_media"):
        return redirect("/projects/")

    if request.method == "POST":
        form = SocialPostForm(request.POST, owner=user, project=project)
        if form.is_valid():
            post = form.save()
            return redirect("social-media-dashboard", project_id=project.id)
    else:
        form = SocialPostForm(owner=user, project=project)

    return render(request, "social_media/post_form.html", {
        "project": project,
        "form": form,
        "title": "Nuovo post",
    })


@login_required
@require_http_methods(["GET", "POST"])
def post_edit(request, project_id, post_id):
    user = request.user
    project = get_object_or_404(Project, id=project_id, owner=user)
    post = get_object_or_404(SocialPost, id=post_id, owner=user, project=project)

    if request.method == "POST":
        form = SocialPostForm(request.POST, instance=post, owner=user, project=project)
        if form.is_valid():
            form.save()
            return redirect("social-media-dashboard", project_id=project.id)
    else:
        form = SocialPostForm(instance=post, owner=user, project=project)

    return render(request, "social_media/post_form.html", {
        "project": project,
        "form": form,
        "post": post,
        "title": "Modifica post",
    })


@login_required
@require_http_methods(["POST"])
def post_status(request, project_id, post_id):
    user = request.user
    project = get_object_or_404(Project, id=project_id, owner=user)
    post = get_object_or_404(SocialPost, id=post_id, owner=user, project=project)
    new_status = request.POST.get("status")
    if new_status in {c[0] for c in SocialPost.Status.choices}:
        post.status = new_status
        if new_status == SocialPost.Status.PUBLISHED and not post.published_at:
            from django.utils import timezone
            post.published_at = timezone.now()
        post.save(update_fields=["status", "published_at", "updated_at"])
    return redirect("social-media-dashboard", project_id=project.id)


@login_required
@require_http_methods(["POST"])
def post_delete(request, project_id, post_id):
    user = request.user
    project = get_object_or_404(Project, id=project_id, owner=user)
    post = get_object_or_404(SocialPost, id=post_id, owner=user, project=project)
    post.delete()
    return redirect("social-media-dashboard", project_id=project.id)
