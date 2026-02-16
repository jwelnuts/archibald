import json
import os
import urllib.error
import urllib.request
from datetime import date

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ArchibaldPromptForm
from .models import ArchibaldMessage, ArchibaldThread
from .services import build_context_messages, build_insight_cards


ARCHIBALD_SYSTEM = (
    "Sei Archibald, il maggiordomo personale dell'utente. "
    "Parla in modo caldo, elegante e amichevole, come un maggiordomo fidato. "
    "Sii chiaro e concreto, ma con un tocco di discrezione. "
    "Rimani centrato esclusivamente sulle funzionalita' di questo progetto (MIO) "
    "e sui dati disponibili nell'app; non proporre app o servizi esterni "
    "a meno che l'utente lo richieda esplicitamente. "
    "Se l'utente chiede fonti esterne o confronti, puoi citarle, ma resta "
    "sempre nel ruolo di assistente di MIO. "
    "Hai pieno accesso ai dati dell'utente corrente in tutte le app del progetto. "
    "Quando utile, chiudi con 1-3 azioni pratiche."
)
def _openai_response(messages):
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return "OPENAI_API_KEY non configurata."

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "instructions": ARCHIBALD_SYSTEM,
        "input": messages,
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else ""
        return f"Errore API: {exc} {detail}"
    except Exception as exc:
        return f"Errore API: {exc}"

    if isinstance(data, dict):
        if data.get("output_text"):
            return data["output_text"]
        output = data.get("output", [])
        for item in output:
            if item.get("type") == "message":
                content = item.get("content", [])
                for block in content:
                    if block.get("type") in {"output_text", "text"}:
                        return block.get("text", "")
    return "Nessuna risposta disponibile."


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
                response_text = _openai_response(messages)
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
    response_text = _openai_response(messages)

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
