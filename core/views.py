from datetime import date, timedelta

from django.contrib import messages as django_messages
from django.contrib.auth import login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import AccountForm, SignUpForm
from .hero_actions import HERO_ACTIONS
from .models import UserHeroActionsConfig
from planner.models import PlannerItem
from routines.models import RoutineItem
from subscriptions.models import Account
from subscriptions.models import SubscriptionOccurrence
from todo.models import Task
from transactions.models import Transaction


def _calendar_events_for_range(user, start: date, end: date):
    events = {}

    def add_event(day, kind, label, count=None):
        key = day.isoformat()
        payload = {"kind": kind, "label": label}
        if count is not None:
            payload["count"] = count
        events.setdefault(key, []).append(payload)

    tasks = (
        Task.objects.filter(owner=user, due_date__range=(start, end))
        .exclude(status=Task.Status.DONE)
        .values("due_date")
        .annotate(count=Count("id"))
    )
    for row in tasks:
        add_event(row["due_date"], "task", "Task", row["count"])

    planner = (
        PlannerItem.objects.filter(owner=user, due_date__range=(start, end), status=PlannerItem.Status.PLANNED)
        .values("due_date")
        .annotate(count=Count("id"))
    )
    for row in planner:
        add_event(row["due_date"], "planner", "Planner", row["count"])

    subs = (
        SubscriptionOccurrence.objects.filter(owner=user, due_date__range=(start, end))
        .values("due_date")
        .annotate(count=Count("id"))
    )
    for row in subs:
        add_event(row["due_date"], "subscription", "Abbonamenti", row["count"])

    tx = (
        Transaction.objects.filter(owner=user, date__range=(start, end))
        .values("date")
        .annotate(count=Count("id"))
    )
    for row in tx:
        add_event(row["date"], "transaction", "Transazioni", row["count"])

    routine_counts = (
        RoutineItem.objects.filter(owner=user, is_active=True)
        .values("weekday")
        .annotate(count=Count("id"))
    )
    routine_map = {row["weekday"]: row["count"] for row in routine_counts}
    if routine_map:
        cursor = start
        while cursor <= end:
            count = routine_map.get(cursor.weekday())
            if count:
                add_event(cursor, "routine", "Routine", count)
            cursor += timedelta(days=1)

    return events


@login_required
def dashboard(request):
    return render(request, "core/dashboard.html")


@login_required
def calendar_events(request):
    start_raw = request.GET.get("start")
    end_raw = request.GET.get("end")
    today = date.today()
    try:
        start = date.fromisoformat(start_raw) if start_raw else today.replace(day=1)
    except ValueError:
        start = today.replace(day=1)
    try:
        end = date.fromisoformat(end_raw) if end_raw else (start + timedelta(days=31))
    except ValueError:
        end = start + timedelta(days=31)

    events = _calendar_events_for_range(request.user, start, end)
    payload = [{"date": day, "items": items} for day, items in events.items()]
    return JsonResponse({"events": payload})


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("/")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


@require_http_methods(["GET", "POST"])
def logout_view(request):
    auth_logout(request)
    return redirect("/")


@login_required
def profile(request):
    from ai_lab.models import ArchibaldInstructionState, ArchibaldPersonaConfig
    from archibald.prompting import build_archibald_system_for_user

    persona, _ = ArchibaldPersonaConfig.objects.get_or_create(owner=request.user)

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        custom_text = (request.POST.get("archibald_custom_instructions") or "").strip()

        if action == "save_archibald_instructions":
            persona.custom_instructions = custom_text
            persona.save()
            django_messages.success(request, "Istruzioni Archibald salvate.")
            return redirect("/profile/")

        if action == "save_archibald_state":
            state_name = (request.POST.get("state_name") or "").strip()
            if not state_name:
                django_messages.error(request, "Inserisci un nome stato prima di salvare.")
            else:
                persona.custom_instructions = custom_text
                persona.save()
                state, created = ArchibaldInstructionState.objects.update_or_create(
                    owner=request.user,
                    name=state_name,
                    defaults={"instructions_text": custom_text},
                )
                label = "creato" if created else "aggiornato"
                django_messages.success(request, f"Stato '{state.name}' {label}.")
            return redirect("/profile/")

        if action == "apply_archibald_state":
            state_id = request.POST.get("state_id")
            state = ArchibaldInstructionState.objects.filter(owner=request.user, id=state_id).first()
            if not state:
                django_messages.error(request, "Stato non trovato.")
            else:
                persona.custom_instructions = state.instructions_text
                persona.save()
                django_messages.success(request, f"Stato '{state.name}' applicato alle istruzioni attive.")
            return redirect("/profile/")

        if action == "delete_archibald_state":
            state_id = request.POST.get("state_id")
            state = ArchibaldInstructionState.objects.filter(owner=request.user, id=state_id).first()
            if not state:
                django_messages.error(request, "Stato non trovato.")
            else:
                label = state.name
                state.delete()
                django_messages.success(request, f"Stato '{label}' eliminato.")
            return redirect("/profile/")

        if action == "save_bias_settings":
            persona.bias_catastrophizing = request.POST.get("bias_catastrophizing") == "on"
            persona.bias_all_or_nothing = request.POST.get("bias_all_or_nothing") == "on"
            persona.bias_overgeneralization = request.POST.get("bias_overgeneralization") == "on"
            persona.bias_mind_reading = request.POST.get("bias_mind_reading") == "on"
            persona.bias_negative_filtering = request.POST.get("bias_negative_filtering") == "on"
            persona.bias_confirmation_bias = request.POST.get("bias_confirmation_bias") == "on"
            persona.save(
                update_fields=[
                    "bias_catastrophizing",
                    "bias_all_or_nothing",
                    "bias_overgeneralization",
                    "bias_mind_reading",
                    "bias_negative_filtering",
                    "bias_confirmation_bias",
                ]
            )
            django_messages.success(request, "Impostazioni bias cognitivi salvate.")
            return redirect("/profile/#bias-cognitivi")

    states = ArchibaldInstructionState.objects.filter(owner=request.user).order_by("-updated_at", "name")
    context = {
        "archibald_custom_instructions": persona.custom_instructions or "",
        "archibald_instruction_states": states[:24],
        "archibald_system_preview": build_archibald_system_for_user(request.user),
        "archibald_persona": persona,
    }
    return render(request, "core/profile.html", context)


@login_required
def hero_actions(request):
    config_obj, _ = UserHeroActionsConfig.objects.get_or_create(user=request.user)
    if request.method == "POST":
        new_config = {}
        for module, actions in HERO_ACTIONS.items():
            enabled = []
            for action in actions:
                key = f"{module}:{action['key']}"
                if request.POST.get(key) == "on":
                    enabled.append(action["key"])
            new_config[module] = enabled
        new_config["_configured"] = True
        config_obj.config = new_config
        config_obj.save(update_fields=["config"])
        return redirect("/profile/hero-actions/")

    selected = config_obj.config or {}
    if selected and not selected.get("_configured"):
        # Backfill legacy config with defaults for missing modules.
        for module, actions in HERO_ACTIONS.items():
            if module not in selected:
                selected[module] = [a["key"] for a in actions if a.get("default")]
        selected["_configured"] = True
        config_obj.config = selected
        config_obj.save(update_fields=["config"])
    context = {
        "actions": HERO_ACTIONS,
        "selected": selected,
    }
    return render(request, "core/hero_actions.html", context)


@login_required
def accounts(request):
    accounts_list = Account.objects.filter(owner=request.user).order_by("name")
    return render(request, "core/accounts.html", {"accounts": accounts_list})


@login_required
def add_account(request):
    if request.method == "POST":
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.owner = request.user
            account.save()
            return redirect("/core/accounts/")
    else:
        form = AccountForm()
    return render(request, "core/add_account.html", {"form": form})


@login_required
def update_account(request):
    account_id = request.GET.get("id")
    account = None
    if account_id:
        account = get_object_or_404(Account, id=account_id, owner=request.user)
        if request.method == "POST":
            form = AccountForm(request.POST, instance=account)
            if form.is_valid():
                form.save()
                return redirect("/core/accounts/")
        else:
            form = AccountForm(instance=account)
        return render(request, "core/update_account.html", {"form": form, "account": account})
    accounts_list = Account.objects.filter(owner=request.user).order_by("name")[:20]
    return render(request, "core/update_account.html", {"accounts": accounts_list})


@login_required
def remove_account(request):
    account_id = request.GET.get("id")
    account = None
    if account_id:
        account = get_object_or_404(Account, id=account_id, owner=request.user)
        if request.method == "POST":
            account.delete()
            return redirect("/core/accounts/")
    accounts_list = Account.objects.filter(owner=request.user).order_by("name")[:20]
    return render(request, "core/remove_account.html", {"account": account, "accounts": accounts_list})
