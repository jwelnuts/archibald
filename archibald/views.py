from datetime import date, datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ArchibaldPromptForm
from .models import ArchibaldMessage, ArchibaldThread
from .openai_client import request_openai_response
from .prompting import build_archibald_system_for_user
from .services import build_context_messages, build_insight_cards

MODE_DIARY = "diary"
MODE_TEMP = "temp"


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


def _resolve_mode(raw_mode):
    mode = (raw_mode or "").strip().lower()
    if mode in {MODE_DIARY, MODE_TEMP}:
        return mode
    return MODE_DIARY


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _message_payload(msg):
    return {
        "id": msg.id,
        "role": msg.role.lower(),
        "content": msg.content,
        "day": msg.created_at.date().isoformat(),
        "time": msg.created_at.strftime("%H:%M"),
        "is_favorite": msg.is_favorite,
        "created_at": msg.created_at.isoformat(),
    }


def _group_messages_by_day(messages):
    grouped_days = []
    current_day = ""
    for msg in messages:
        msg_day = msg.created_at.date().isoformat()
        if msg_day != current_day:
            grouped_days.append({"day": msg_day, "messages": []})
            current_day = msg_day
        grouped_days[-1]["messages"].append(msg)
    return grouped_days


def _parse_day_or_today(raw_day):
    if not raw_day:
        return date.today()
    try:
        return date.fromisoformat(raw_day)
    except ValueError:
        return date.today()


def _diary_thread(user):
    thread = (
        ArchibaldThread.objects.filter(owner=user, kind=ArchibaldThread.Kind.DIARY, is_active=True)
        .order_by("-updated_at", "-id")
        .first()
    )
    if thread:
        return thread

    legacy = ArchibaldThread.objects.filter(owner=user, is_active=True).order_by("-updated_at", "-id").first()
    if legacy:
        if legacy.kind != ArchibaldThread.Kind.DIARY:
            legacy.kind = ArchibaldThread.Kind.DIARY
            legacy.save(update_fields=["kind", "updated_at"])
        return legacy

    return ArchibaldThread.objects.create(
        owner=user,
        title="Diario Archibald",
        is_active=True,
        kind=ArchibaldThread.Kind.DIARY,
    )


def _temporary_threads(user):
    return list(
        ArchibaldThread.objects.filter(owner=user, kind=ArchibaldThread.Kind.TEMPORARY)
        .annotate(last_message_at=Max("messages__created_at"), messages_total=Count("messages"))
        .order_by("-last_message_at", "-updated_at", "-id")[:50]
    )


def _temporary_thread_by_id(user, raw_thread_id):
    try:
        thread_id = int(raw_thread_id)
    except (TypeError, ValueError):
        return None
    return (
        ArchibaldThread.objects.filter(
            owner=user,
            id=thread_id,
            kind=ArchibaldThread.Kind.TEMPORARY,
        )
        .order_by("-id")
        .first()
    )


def _build_temp_thread_title(prompt):
    compact = " ".join((prompt or "").split())
    if compact:
        if len(compact) > 70:
            compact = f"{compact[:67].rstrip()}..."
        return compact
    return f"Chat temporanea {datetime.now().strftime('%d/%m %H:%M')}"


def _chat_messages_for_diary(user, thread, selected_day):
    rows = list(
        ArchibaldMessage.objects.filter(owner=user, thread=thread)
        .filter(created_at__date=selected_day)
        .order_by("-id")[:50]
    )
    rows.reverse()
    return rows


def _chat_messages_for_temp(user, thread):
    if not thread:
        return []
    rows = list(ArchibaldMessage.objects.filter(owner=user, thread=thread).order_by("-id")[:80])
    rows.reverse()
    return rows


@login_required
def dashboard(request):
    user = request.user
    mode = _resolve_mode(request.GET.get("mode"))
    today = date.today()

    diary_thread = _diary_thread(user)
    selected_day = _parse_day_or_today(request.GET.get("day"))

    temporary_threads = _temporary_threads(user)
    selected_temp_thread = None
    if mode == MODE_TEMP:
        selected_temp_thread = _temporary_thread_by_id(user, request.GET.get("thread"))
        if not selected_temp_thread and temporary_threads:
            selected_temp_thread = temporary_threads[0]

    if request.method == "POST":
        form = ArchibaldPromptForm(request.POST)
        if form.is_valid():
            prompt = form.cleaned_data["prompt"].strip()
            post_mode = _resolve_mode(request.POST.get("mode") or mode)
            if prompt:
                if post_mode == MODE_DIARY:
                    active_thread = diary_thread
                else:
                    active_thread = _temporary_thread_by_id(user, request.POST.get("thread_id"))
                    if not active_thread:
                        active_thread = ArchibaldThread.objects.create(
                            owner=user,
                            is_active=False,
                            kind=ArchibaldThread.Kind.TEMPORARY,
                            title=_build_temp_thread_title(prompt),
                        )

                history = list(
                    ArchibaldMessage.objects.filter(owner=user, thread=active_thread).order_by("-created_at")[:10]
                )
                history.reverse()
                messages = _build_messages(history, prompt)
                messages = build_context_messages(user, prompt) + messages
                response_text = _openai_response(user, messages)

                with transaction.atomic():
                    user_msg = ArchibaldMessage.objects.create(
                        owner=user,
                        thread=active_thread,
                        role=ArchibaldMessage.Role.USER,
                        content=prompt,
                    )
                    assistant_msg = ArchibaldMessage.objects.create(
                        owner=user,
                        thread=active_thread,
                        role=ArchibaldMessage.Role.ASSISTANT,
                        content=response_text,
                    )

                if _is_ajax(request):
                    return JsonResponse(
                        {
                            "mode": post_mode,
                            "thread": {
                                "id": active_thread.id,
                                "title": active_thread.title,
                                "kind": active_thread.kind,
                            },
                            "user": _message_payload(user_msg),
                            "assistant": _message_payload(assistant_msg),
                        }
                    )

                if post_mode == MODE_DIARY:
                    return redirect(f"/archibald/?mode={MODE_DIARY}&day={user_msg.created_at.date().isoformat()}")
                return redirect(f"/archibald/?mode={MODE_TEMP}&thread={active_thread.id}")
    else:
        form = ArchibaldPromptForm()

    if mode == MODE_DIARY:
        messages = _chat_messages_for_diary(user, diary_thread, selected_day)
        diary_days = list(
            ArchibaldMessage.objects.filter(owner=user, thread=diary_thread).dates("created_at", "day", order="DESC")
        )
        active_thread = diary_thread
    else:
        messages = _chat_messages_for_temp(user, selected_temp_thread)
        diary_days = []
        active_thread = selected_temp_thread

    grouped_days = _group_messages_by_day(messages)

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
            "mode": mode,
            "mode_diary": MODE_DIARY,
            "mode_temp": MODE_TEMP,
            "temporary_threads": temporary_threads,
            "selected_temp_thread": selected_temp_thread,
            "active_thread": active_thread,
        },
    )


@login_required
def messages_api(request):
    mode = _resolve_mode(request.GET.get("mode"))
    before_id = request.GET.get("before")

    if mode == MODE_DIARY:
        thread = _diary_thread(request.user)
        selected_day = _parse_day_or_today(request.GET.get("day"))
        qs = ArchibaldMessage.objects.filter(owner=request.user, thread=thread).filter(created_at__date=selected_day)
    else:
        thread = _temporary_thread_by_id(request.user, request.GET.get("thread"))
        if not thread:
            return JsonResponse({"messages": []})
        qs = ArchibaldMessage.objects.filter(owner=request.user, thread=thread)

    qs = qs.order_by("-id")
    if before_id:
        try:
            qs = qs.filter(id__lt=int(before_id))
        except ValueError:
            pass

    items = list(qs[:20])
    items.reverse()
    payload = [_message_payload(msg) for msg in items]
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
def create_temp_thread(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Metodo non consentito."}, status=405)

    title = (request.POST.get("title") or "").strip()
    thread = ArchibaldThread.objects.create(
        owner=request.user,
        is_active=False,
        kind=ArchibaldThread.Kind.TEMPORARY,
        title=(title[:120] if title else _build_temp_thread_title("")),
    )

    if _is_ajax(request):
        return JsonResponse({"ok": True, "thread_id": thread.id, "title": thread.title})
    return redirect(f"/archibald/?mode={MODE_TEMP}&thread={thread.id}")


@login_required
def remove_temp_thread(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Metodo non consentito."}, status=405)

    thread = get_object_or_404(
        ArchibaldThread,
        owner=request.user,
        id=request.POST.get("thread_id"),
        kind=ArchibaldThread.Kind.TEMPORARY,
    )
    thread.delete()

    if _is_ajax(request):
        return JsonResponse({"ok": True})
    return redirect(f"/archibald/?mode={MODE_TEMP}")


@login_required
def quick_chat(request):
    if request.method != "POST":
        return JsonResponse({"error": "Metodo non consentito."}, status=405)

    prompt = (request.POST.get("prompt") or "").strip()
    if not prompt:
        return JsonResponse({"error": "Messaggio vuoto."}, status=400)

    thread = _temporary_thread_by_id(request.user, request.POST.get("thread_id"))
    if not thread:
        thread = ArchibaldThread.objects.create(
            owner=request.user,
            is_active=False,
            kind=ArchibaldThread.Kind.TEMPORARY,
            title=f"Dashboard {date.today().isoformat()}",
        )

    history = list(ArchibaldMessage.objects.filter(owner=request.user, thread=thread).order_by("-created_at")[:10])
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
            "thread_title": thread.title,
            "user": _message_payload(user_msg),
            "assistant": _message_payload(assistant_msg),
        }
    )
