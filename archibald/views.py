from datetime import date

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ArchibaldPromptForm
from .models import ArchibaldMessage, ArchibaldThread
from .openai_client import request_openai_response
from .prompting import build_archibald_system_for_user
from .services import build_context_messages, build_insight_cards


def _openai_response(user, messages):
    instructions = build_archibald_system_for_user(user)
    return request_openai_response(messages, instructions)


def _build_messages(history, user_text):
    messages = []
    for msg in history:
        role = msg.role.lower()
        messages.append(
            {
                "role": role,
                "content": msg.content,
            }
        )
    messages.append(
        {
            "role": "user",
            "content": user_text,
        }
    )
    return messages


@login_required
def dashboard(request):
    thread, _ = ArchibaldThread.objects.get_or_create(owner=request.user, is_active=True)
    today = date.today()
    day_param = request.GET.get("day")
    try:
        selected_day = date.fromisoformat(day_param) if day_param else today
    except ValueError:
        selected_day = today
    diary_days = list(
        ArchibaldMessage.objects.filter(owner=request.user, thread=thread)
        .dates("created_at", "day", order="DESC")
    )
    messages = (
        ArchibaldMessage.objects.filter(owner=request.user, thread=thread)
        .filter(created_at__date=selected_day)
        .order_by("-id")[:30]
    )
    messages = list(messages)
    messages.reverse()
    grouped_days = []
    current_day = None
    for msg in messages:
        msg_day = msg.created_at.date().isoformat()
        if msg_day != current_day:
            grouped_days.append({"day": msg_day, "messages": []})
            current_day = msg_day
        grouped_days[-1]["messages"].append(msg)

    if request.method == "POST":
        form = ArchibaldPromptForm(request.POST)
        if form.is_valid():
            prompt = form.cleaned_data["prompt"].strip()
            if prompt:
                history = list(
                    ArchibaldMessage.objects.filter(owner=request.user, thread=thread)
                    .order_by("-created_at")[:10]
                )
                history.reverse()
                messages = _build_messages(history, prompt)
                messages = build_context_messages(request.user, prompt) + messages
                response_text = _openai_response(request.user, messages)
                with transaction.atomic():
                    user_msg = ArchibaldMessage.objects.create(
                        owner=request.user,
                        thread=thread,
                        role=ArchibaldMessage.Role.USER,
                        content=prompt,
                    )
                    assistant_msg = ArchibaldMessage.objects.create(
                        owner=request.user,
                        thread=thread,
                        role=ArchibaldMessage.Role.ASSISTANT,
                        content=response_text,
                    )
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "user": {
                                "id": user_msg.id,
                                "role": "user",
                                "content": user_msg.content,
                                "day": user_msg.created_at.date().isoformat(),
                                "time": user_msg.created_at.strftime("%H:%M"),
                                "is_favorite": user_msg.is_favorite,
                                "created_at": user_msg.created_at.isoformat(),
                            },
                            "assistant": {
                                "id": assistant_msg.id,
                                "role": "assistant",
                                "content": assistant_msg.content,
                                "day": assistant_msg.created_at.date().isoformat(),
                                "time": assistant_msg.created_at.strftime("%H:%M"),
                                "is_favorite": assistant_msg.is_favorite,
                                "created_at": assistant_msg.created_at.isoformat(),
                            },
                        }
                    )
                return redirect("/archibald/")
    else:
        form = ArchibaldPromptForm()

    return render(
        request,
        "archibald/dashboard.html",
        {
            "form": form,
            "messages": messages,
            "grouped_days": grouped_days,
            "today": today,
            "selected_day": selected_day,
            "diary_days": diary_days,
        },
    )


@login_required
def messages_api(request):
    thread = ArchibaldThread.objects.filter(owner=request.user, is_active=True).first()
    if not thread:
        return JsonResponse({"messages": []})

    today = date.today()
    day_param = request.GET.get("day")
    try:
        selected_day = date.fromisoformat(day_param) if day_param else today
    except ValueError:
        selected_day = today
    before_id = request.GET.get("before")
    qs = (
        ArchibaldMessage.objects.filter(owner=request.user, thread=thread)
        .filter(created_at__date=selected_day)
        .order_by("-id")
    )
    if before_id:
        try:
            before_id = int(before_id)
            qs = qs.filter(id__lt=before_id)
        except ValueError:
            pass

    items = list(qs[:20])
    items.reverse()
    payload = [
        {
            "id": msg.id,
            "role": msg.role.lower(),
            "content": msg.content,
            "day": msg.created_at.date().isoformat(),
            "time": msg.created_at.strftime("%H:%M"),
            "is_favorite": msg.is_favorite,
            "created_at": msg.created_at.isoformat(),
        }
        for msg in items
    ]
    return JsonResponse({"messages": payload})


@login_required
def toggle_favorite(request):
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)
    msg_id = request.POST.get("id")
    msg = get_object_or_404(ArchibaldMessage, id=msg_id, owner=request.user)
    msg.is_favorite = not msg.is_favorite
    msg.save(update_fields=["is_favorite"])
    return JsonResponse({"ok": True, "id": msg.id, "is_favorite": msg.is_favorite})


@login_required
def insights(request):
    kind = request.GET.get("kind", "overview")
    cards = build_insight_cards(request.user, kind)
    return render(request, "archibald/partials/insight_cards.html", {"cards": cards})


@login_required
def quick_chat(request):
    if request.method != "POST":
        return JsonResponse({"error": "Metodo non consentito."}, status=405)
    prompt = (request.POST.get("prompt") or "").strip()
    if not prompt:
        return JsonResponse({"error": "Messaggio vuoto."}, status=400)

    thread_id = request.POST.get("thread_id")
    thread = None
    if thread_id:
        try:
            thread = ArchibaldThread.objects.get(id=thread_id, owner=request.user)
        except ArchibaldThread.DoesNotExist:
            thread = None
    if not thread:
        thread = ArchibaldThread.objects.create(
            owner=request.user,
            is_active=False,
            title=f"Dashboard {date.today().isoformat()}",
        )

    history = list(
        ArchibaldMessage.objects.filter(owner=request.user, thread=thread)
        .order_by("-created_at")[:10]
    )
    history.reverse()
    messages = build_context_messages(request.user, prompt) + _build_messages(history, prompt)
    response_text = _openai_response(request.user, messages)

    with transaction.atomic():
        user_msg = ArchibaldMessage.objects.create(
            owner=request.user,
            thread=thread,
            role=ArchibaldMessage.Role.USER,
            content=prompt,
        )
        assistant_msg = ArchibaldMessage.objects.create(
            owner=request.user,
            thread=thread,
            role=ArchibaldMessage.Role.ASSISTANT,
            content=response_text,
        )

    return JsonResponse(
        {
            "thread_id": thread.id,
            "user": {
                "id": user_msg.id,
                "role": "user",
                "content": user_msg.content,
                "day": user_msg.created_at.date().isoformat(),
                "time": user_msg.created_at.strftime("%H:%M"),
                "created_at": user_msg.created_at.isoformat(),
            },
            "assistant": {
                "id": assistant_msg.id,
                "role": "assistant",
                "content": assistant_msg.content,
                "day": assistant_msg.created_at.date().isoformat(),
                "time": assistant_msg.created_at.strftime("%H:%M"),
                "created_at": assistant_msg.created_at.isoformat(),
            },
        }
    )
