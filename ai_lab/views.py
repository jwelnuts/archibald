from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from archibald.openai_client import request_openai_response
from archibald.prompting import build_archibald_system_for_user

from .forms import ArchibaldPersonaConfigForm, ArchibaldSandboxPromptForm, LabEntryForm
from .models import ArchibaldPersonaConfig, LabEntry


@login_required
def dashboard(request):
    status_filter = (request.GET.get("status") or "").upper()
    entries = LabEntry.objects.filter(owner=request.user).order_by("-updated_at")
    if status_filter in LabEntry.Status.values:
        entries = entries.filter(status=status_filter)

    persona, _ = ArchibaldPersonaConfig.objects.get_or_create(owner=request.user)
    persona_form = ArchibaldPersonaConfigForm(instance=persona)
    sandbox_form = ArchibaldSandboxPromptForm()
    sandbox_prompt = ""
    sandbox_result = ""
    system_preview = build_archibald_system_for_user(request.user)

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "save_persona":
            persona_form = ArchibaldPersonaConfigForm(request.POST, instance=persona)
            if persona_form.is_valid():
                persona_form.save()
                django_messages.success(request, "Profilo Archibald salvato.")
                return redirect("/ai-lab/")
        elif action == "test_persona":
            sandbox_form = ArchibaldSandboxPromptForm(request.POST)
            if sandbox_form.is_valid():
                sandbox_prompt = (sandbox_form.cleaned_data.get("prompt") or "").strip()
                if sandbox_prompt:
                    messages = [
                        {
                            "role": "user",
                            "content": sandbox_prompt,
                        }
                    ]
                    system_preview = build_archibald_system_for_user(request.user)
                    sandbox_result = request_openai_response(messages, system_preview)

    status_cards = [
        {
            "code": status,
            "label": label,
            "count": LabEntry.objects.filter(owner=request.user, status=status).count(),
        }
        for status, label in LabEntry.Status.choices
    ]
    return render(
        request,
        "ai_lab/dashboard.html",
        {
            "entries": entries[:100],
            "status_filter": status_filter,
            "status_choices": LabEntry.Status.choices,
            "status_cards": status_cards,
            "persona_form": persona_form,
            "sandbox_form": sandbox_form,
            "sandbox_prompt": sandbox_prompt,
            "sandbox_result": sandbox_result,
            "system_preview": system_preview,
            "psychological_field_names": ArchibaldPersonaConfigForm.PSYCHOLOGICAL_BOOLEAN_FIELDS,
        },
    )


@login_required
def add_item(request):
    if request.method == "POST":
        form = LabEntryForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            return redirect("/ai-lab/")
    else:
        form = LabEntryForm()
    return render(request, "ai_lab/add_item.html", {"form": form})


@login_required
def update_item(request):
    item_id = request.GET.get("id")
    if not item_id:
        return redirect("/ai-lab/")
    item = get_object_or_404(LabEntry, id=item_id, owner=request.user)
    if request.method == "POST":
        form = LabEntryForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return redirect("/ai-lab/")
    else:
        form = LabEntryForm(instance=item)
    return render(request, "ai_lab/update_item.html", {"form": form, "item": item})


@login_required
def remove_item(request):
    item_id = request.GET.get("id")
    if not item_id:
        return redirect("/ai-lab/")
    item = get_object_or_404(LabEntry, id=item_id, owner=request.user)
    if request.method == "POST":
        item.delete()
        return redirect("/ai-lab/")
    return render(request, "ai_lab/remove_item.html", {"item": item})
