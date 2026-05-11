from calendar import Calendar
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
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

    # KPI
    channels = SocialChannel.objects.filter(owner=user, project=project).order_by("platform", "name")
    active_channels = channels.filter(is_active=True)
    posts_qs = SocialPost.objects.filter(owner=user, project=project)

    total_posts = posts_qs.count()
    draft_count = posts_qs.filter(status=SocialPost.Status.DRAFT).count()
    scheduled_count = posts_qs.filter(status=SocialPost.Status.SCHEDULED).count()
    published_count = posts_qs.filter(status=SocialPost.Status.PUBLISHED).count()
    archived_count = posts_qs.filter(status=SocialPost.Status.ARCHIVED).count()

    # Upcoming scheduled posts (next 7 days)
    today = timezone.now().date()
    week_end = today + timedelta(days=7)
    upcoming = (
        posts_qs.filter(status=SocialPost.Status.SCHEDULED, scheduled_at__date__range=(today, week_end))
        .select_related("channel")
        .order_by("scheduled_at")[:10]
    )

    # Recent feed
    recent_posts = (
        posts_qs.select_related("channel")
        .order_by("-created_at")[:15]
    )

    # Calendar month view
    month_raw = request.GET.get("month")
    if month_raw:
        try:
            month_start = date.fromisoformat(f"{month_raw}-01")
        except (ValueError, TypeError):
            month_start = today.replace(day=1)
    else:
        month_start = today.replace(day=1)
    month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    month_param = month_start.strftime("%Y-%m")
    prev_month = (month_start - timedelta(days=1)).strftime("%Y-%m")
    next_month = (month_start + timedelta(days=32)).replace(day=1).strftime("%Y-%m")

    cal_posts = (
        posts_qs.filter(
            Q(scheduled_at__date__range=(month_start, month_end)) |
            Q(published_at__date__range=(month_start, month_end)) |
            Q(created_at__date__range=(month_start, month_end), status=SocialPost.Status.DRAFT)
        )
        .select_related("channel")
        .order_by("scheduled_at", "published_at", "created_at")
    )

    day_posts = {}
    for p in cal_posts:
        d = p.scheduled_at.date() if p.scheduled_at else (p.published_at.date() if p.published_at else p.created_at.date())
        if d not in day_posts:
            day_posts[d] = []
        day_posts[d].append(p)

    cal = Calendar(firstweekday=0)
    weeks_raw = cal.monthdayscalendar(month_start.year, month_start.month)
    calendar_weeks = []
    for week in weeks_raw:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
            else:
                d = date(month_start.year, month_start.month, day)
                week_data.append({
                    "day": day,
                    "iso": d.isoformat(),
                    "is_today": d == today,
                    "posts": day_posts.get(d, []),
                })
        calendar_weeks.append(week_data)

    # Stats per channel
    channel_stats = []
    for ch in channels:
        ch_posts = posts_qs.filter(channel=ch)
        channel_stats.append({
            "channel": ch,
            "total": ch_posts.count(),
            "draft": ch_posts.filter(status=SocialPost.Status.DRAFT).count(),
            "scheduled": ch_posts.filter(status=SocialPost.Status.SCHEDULED).count(),
            "published": ch_posts.filter(status=SocialPost.Status.PUBLISHED).count(),
        })

    context = {
        "project": project,
        "channels": channels,
        "active_channels_count": active_channels.count(),
        "total_posts": total_posts,
        "draft_count": draft_count,
        "scheduled_count": scheduled_count,
        "published_count": published_count,
        "archived_count": archived_count,
        "upcoming": upcoming,
        "recent_posts": recent_posts,
        "calendar_weeks": calendar_weeks,
        "month_label": month_start.strftime("%B %Y"),
        "month_param": month_param,
        "prev_month": prev_month,
        "next_month": next_month,
        "channel_stats": channel_stats,
        "today": today,
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
        form = SocialPostForm(request.POST, request.FILES, owner=user, project=project)
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
        form = SocialPostForm(request.POST, request.FILES, instance=post, owner=user, project=project)
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
