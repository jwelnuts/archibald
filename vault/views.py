from datetime import timedelta
from urllib.parse import quote

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import VaultItemForm, VaultSetupForm, VaultUnlockForm
from .models import VaultItem, VaultProfile
from .qr import otpauth_qr_data_uri
from .session import clear_verified, is_verified, mark_verified
from .totp import generate_secret, provisioning_uri, verify_code

MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 5


def _profile_for(user):
    profile, _ = VaultProfile.objects.get_or_create(owner=user)
    return profile


def _vault_gate(request):
    profile = _profile_for(request.user)
    if not profile.totp_enabled_at:
        return redirect("/vault/setup")
    if not is_verified(request):
        next_url = quote(request.get_full_path())
        return redirect(f"/vault/unlock?next={next_url}")
    return None


def _safe_read(value_getter):
    try:
        return value_getter()
    except ValueError:
        return "[contenuto non leggibile]"


@login_required
def dashboard(request):
    gate = _vault_gate(request)
    if gate:
        return gate

    kind_filter = (request.GET.get("kind") or "").upper()
    items = VaultItem.objects.filter(owner=request.user).order_by("-updated_at")
    if kind_filter in VaultItem.Kind.values:
        items = items.filter(kind=kind_filter)

    rows = []
    for item in items[:100]:
        notes = _safe_read(item.get_notes_value)
        rows.append(
            {
                "id": item.id,
                "title": item.title,
                "kind_label": item.get_kind_display(),
                "login": item.login or "-",
                "website_url": item.website_url or "",
                "masked_secret": _safe_read(item.masked_secret),
                "notes_preview": notes[:120] + ("..." if len(notes) > 120 else ""),
                "updated_at": item.updated_at,
            }
        )

    return render(
        request,
        "vault/dashboard.html",
        {
            "rows": rows,
            "kind_filter": kind_filter,
            "kind_choices": VaultItem.Kind.choices,
        },
    )


@login_required
def setup_totp(request):
    profile = _profile_for(request.user)
    if profile.totp_enabled_at:
        # Setup one-time: dopo l'attivazione iniziale non si espone piu il segreto.
        return redirect("/vault/unlock")

    secret = ""
    if profile.totp_secret_encrypted:
        secret = _safe_read(profile.get_totp_secret)
    if not secret or secret.startswith("["):
        secret = generate_secret()
        profile.set_totp_secret(secret)
        profile.save(update_fields=["totp_secret_encrypted", "updated_at"])

    form = VaultSetupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        code = form.cleaned_data["code"]
        if verify_code(secret, code):
            profile.totp_enabled_at = timezone.now()
            profile.failed_attempts = 0
            profile.locked_until = None
            profile.save(update_fields=["totp_enabled_at", "failed_attempts", "locked_until", "updated_at"])
            mark_verified(request)
            return redirect(request.GET.get("next") or "/vault/")
        form.add_error("code", "Codice non valido. Controlla l'orario del telefono.")

    context = {
        "form": form,
        "manual_key": secret,
        "otpauth_uri": provisioning_uri(request.user.username, secret),
        "already_enabled": bool(profile.totp_enabled_at),
    }
    context["qr_data_uri"] = otpauth_qr_data_uri(context["otpauth_uri"])
    return render(request, "vault/setup_totp.html", context)


@login_required
def unlock(request):
    profile = _profile_for(request.user)
    if not profile.totp_enabled_at:
        return redirect("/vault/setup")
    if is_verified(request):
        return redirect(request.GET.get("next") or "/vault/")

    now = timezone.now()
    lock_seconds = 0
    if profile.locked_until and profile.locked_until > now:
        lock_seconds = int((profile.locked_until - now).total_seconds())

    form = VaultUnlockForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if lock_seconds > 0:
            form.add_error("code", f"Vault bloccato temporaneamente. Riprova tra {lock_seconds} secondi.")
        else:
            secret = _safe_read(profile.get_totp_secret)
            if verify_code(secret, form.cleaned_data["code"]):
                profile.failed_attempts = 0
                profile.locked_until = None
                profile.save(update_fields=["failed_attempts", "locked_until", "updated_at"])
                mark_verified(request)
                return redirect(request.GET.get("next") or "/vault/")
            profile.failed_attempts = (profile.failed_attempts or 0) + 1
            if profile.failed_attempts >= MAX_FAILED_ATTEMPTS:
                profile.failed_attempts = 0
                profile.locked_until = now + timedelta(minutes=LOCK_MINUTES)
            profile.save(update_fields=["failed_attempts", "locked_until", "updated_at"])
            form.add_error("code", "Codice non valido.")

    return render(
        request,
        "vault/unlock.html",
        {
            "form": form,
            "lock_seconds": lock_seconds,
        },
    )


@login_required
def lock(request):
    clear_verified(request)
    return redirect("/vault/unlock")


@login_required
def add_item(request):
    gate = _vault_gate(request)
    if gate:
        return gate

    form = VaultItemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.owner = request.user
        item.save()
        return redirect("/vault/")
    return render(request, "vault/add_item.html", {"form": form})


@login_required
def update_item(request):
    gate = _vault_gate(request)
    if gate:
        return gate

    item_id = request.GET.get("id")
    if not item_id:
        return redirect("/vault/")
    item = get_object_or_404(VaultItem, id=item_id, owner=request.user)
    form = VaultItemForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("/vault/")
    return render(request, "vault/update_item.html", {"form": form, "item": item})


@login_required
def remove_item(request):
    gate = _vault_gate(request)
    if gate:
        return gate

    item_id = request.GET.get("id")
    if not item_id:
        return redirect("/vault/")
    item = get_object_or_404(VaultItem, id=item_id, owner=request.user)
    if request.method == "POST":
        item.delete()
        return redirect("/vault/")
    return render(request, "vault/remove_item.html", {"item": item})
