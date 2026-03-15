from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .actions import (
    ensure_default_flag_rules,
    execute_action_manually,
    list_action_choices,
    list_supported_email_actions,
)
from .forms import ArchibaldEmailFlagRuleForm, ArchibaldMailboxConfigForm, SendTestEmailForm
from .models import ArchibaldEmailFlagRule, ArchibaldEmailMessage, ArchibaldMailboxConfig
from .services import (
    ArchibaldMailError,
    process_inbox_for_config,
    send_notification_for_config,
    send_test_email,
)


@login_required
def dashboard(request):
    config, _ = ArchibaldMailboxConfig.objects.get_or_create(owner=request.user)
    ensure_default_flag_rules(request.user)
    config_form = ArchibaldMailboxConfigForm(instance=config)
    test_form = SendTestEmailForm(
        initial={
            "recipient": config.notification_target(),
            "subject": "Test Archibald Mail",
            "body": "Test operativo: il canale SMTP di Archibald risulta attivo.",
        }
    )

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "save_config":
            config_form = ArchibaldMailboxConfigForm(request.POST, instance=config)
            if config_form.is_valid():
                config_form.save()
                django_messages.success(request, "Configurazione Archibald Mail salvata.")
                return redirect("/archibald-mail/")
        elif action == "process_inbox":
            try:
                result = process_inbox_for_config(config, force=True)
                django_messages.success(
                    request,
                    (
                        "Inbox processata: "
                        f"fetched={result['fetched']} replied={result['replied']} "
                        f"skipped={result['skipped']} failed={result['failed']}"
                    ),
                )
            except Exception as exc:
                django_messages.error(request, f"Errore processazione inbox: {exc}")
            return redirect("/archibald-mail/")
        elif action == "send_notification":
            try:
                result = send_notification_for_config(config, force=True, only_due=False)
                if result.get("sent"):
                    django_messages.success(request, "Notifica Archibald inviata.")
                else:
                    django_messages.warning(request, f"Notifica non inviata: {result.get('reason', 'n/a')}")
            except Exception as exc:
                django_messages.error(request, f"Errore invio notifica: {exc}")
            return redirect("/archibald-mail/")
        elif action == "send_test_email":
            test_form = SendTestEmailForm(request.POST)
            if test_form.is_valid():
                try:
                    send_test_email(
                        config,
                        recipient=test_form.cleaned_data["recipient"],
                        subject=test_form.cleaned_data["subject"],
                        body=test_form.cleaned_data["body"],
                    )
                    django_messages.success(request, "Email di test inviata con successo.")
                except ArchibaldMailError as exc:
                    django_messages.error(request, f"Errore email di test: {exc}")
                return redirect("/archibald-mail/")

    recent_messages = list(
        ArchibaldEmailMessage.objects.filter(owner=request.user, config=config)
        .order_by("-created_at")[:60]
    )
    status_cards = list(
        ArchibaldEmailMessage.objects.filter(owner=request.user, config=config)
        .values("status")
        .annotate(total=Count("id"))
        .order_by("status")
    )
    inbound_pending_count = ArchibaldEmailMessage.objects.filter(
        owner=request.user,
        direction=ArchibaldEmailMessage.Direction.INBOUND,
        review_status=ArchibaldEmailMessage.ReviewStatus.PENDING,
    ).count()

    return render(
        request,
        "archibald_mail/dashboard.html",
        {
            "config": config,
            "config_form": config_form,
            "core_field_names": ArchibaldMailboxConfigForm.CORE_FIELDS,
            "notification_field_names": ArchibaldMailboxConfigForm.NOTIFICATION_FIELDS,
            "test_form": test_form,
            "recent_messages": recent_messages,
            "status_cards": status_cards,
            "imap_host_value": config.resolved_imap_host(),
            "imap_port_value": config.resolved_imap_port(),
            "imap_username_value": config.resolved_imap_username(),
            "imap_password_configured": bool(config.resolved_imap_password()),
            "smtp_host_value": config.resolved_smtp_host(),
            "smtp_port_value": config.resolved_smtp_port(),
            "smtp_username_value": config.resolved_smtp_username(),
            "smtp_sender_value": config.smtp_sender(),
            "smtp_password_configured": bool(config.resolved_smtp_password()),
            "available_email_actions": list_supported_email_actions(request.user),
            "inbound_pending_count": inbound_pending_count,
        },
    )


@login_required
def flag_rules(request):
    ensure_default_flag_rules(request.user)
    rules = list(
        ArchibaldEmailFlagRule.objects.filter(owner=request.user).order_by("-is_active", "action_key", "flag_token")
    )
    return render(
        request,
        "archibald_mail/flag_rules.html",
        {
            "rules": rules,
        },
    )


@login_required
def add_flag_rule(request):
    if request.method == "POST":
        form = ArchibaldEmailFlagRuleForm(request.POST)
        if form.is_valid():
            row = form.save(commit=False)
            row.owner = request.user
            row.save()
            django_messages.success(request, f"Flag {row.flag_token} creato.")
            return redirect("/archibald-mail/flags/")
    else:
        form = ArchibaldEmailFlagRuleForm()
    return render(
        request,
        "archibald_mail/flag_rule_form.html",
        {
            "form": form,
            "is_edit": False,
            "title": "Nuovo flag inbound",
        },
    )


@login_required
def edit_flag_rule(request, rule_id: int):
    row = get_object_or_404(ArchibaldEmailFlagRule, id=rule_id, owner=request.user)
    if request.method == "POST":
        form = ArchibaldEmailFlagRuleForm(request.POST, instance=row)
        if form.is_valid():
            row = form.save()
            django_messages.success(request, f"Flag {row.flag_token} aggiornato.")
            return redirect("/archibald-mail/flags/")
    else:
        form = ArchibaldEmailFlagRuleForm(instance=row)
    return render(
        request,
        "archibald_mail/flag_rule_form.html",
        {
            "form": form,
            "is_edit": True,
            "title": "Modifica flag inbound",
            "row": row,
        },
    )


@login_required
def remove_flag_rule(request, rule_id: int):
    row = get_object_or_404(ArchibaldEmailFlagRule, id=rule_id, owner=request.user)
    if request.method == "POST":
        token = row.flag_token
        row.delete()
        django_messages.success(request, f"Flag {token} rimosso.")
        return redirect("/archibald-mail/flags/")
    return render(
        request,
        "archibald_mail/flag_rule_delete.html",
        {
            "row": row,
        },
    )


@login_required
def inbound_queue(request):
    status_filter = (request.GET.get("status") or ArchibaldEmailMessage.ReviewStatus.PENDING).strip().upper()
    query = (request.GET.get("q") or "").strip()

    qs = ArchibaldEmailMessage.objects.filter(
        owner=request.user,
        direction=ArchibaldEmailMessage.Direction.INBOUND,
    )
    if status_filter in {
        ArchibaldEmailMessage.ReviewStatus.PENDING,
        ArchibaldEmailMessage.ReviewStatus.APPLIED,
        ArchibaldEmailMessage.ReviewStatus.IGNORED,
    }:
        qs = qs.filter(review_status=status_filter)
    if query:
        qs = qs.filter(subject__icontains=query)

    rows = list(qs.order_by("-created_at")[:120])
    counts = {
        "pending": ArchibaldEmailMessage.objects.filter(
            owner=request.user,
            direction=ArchibaldEmailMessage.Direction.INBOUND,
            review_status=ArchibaldEmailMessage.ReviewStatus.PENDING,
        ).count(),
        "applied": ArchibaldEmailMessage.objects.filter(
            owner=request.user,
            direction=ArchibaldEmailMessage.Direction.INBOUND,
            review_status=ArchibaldEmailMessage.ReviewStatus.APPLIED,
        ).count(),
        "ignored": ArchibaldEmailMessage.objects.filter(
            owner=request.user,
            direction=ArchibaldEmailMessage.Direction.INBOUND,
            review_status=ArchibaldEmailMessage.ReviewStatus.IGNORED,
        ).count(),
    }

    return render(
        request,
        "archibald_mail/inbound_queue.html",
        {
            "rows": rows,
            "status_filter": status_filter,
            "query": query,
            "counts": counts,
            "action_choices": list_action_choices(request.user),
        },
    )


@login_required
def apply_inbound_message(request, message_id: int):
    if request.method != "POST":
        return redirect("/archibald-mail/inbox/")

    row = get_object_or_404(
        ArchibaldEmailMessage,
        id=message_id,
        owner=request.user,
        direction=ArchibaldEmailMessage.Direction.INBOUND,
    )
    action_key = (request.POST.get("action_key") or "").strip()
    category = (request.POST.get("classification_label") or "").strip()
    notes = (request.POST.get("review_notes") or "").strip()

    if not action_key:
        row.classification_label = category[:80]
        row.review_notes = notes[:3000]
        row.save(update_fields=["classification_label", "review_notes", "updated_at"])
        django_messages.success(request, "Classificazione salvata (nessuna azione applicata).")
        return redirect("/archibald-mail/inbox/")

    outcome = execute_action_manually(
        owner=request.user,
        message=row,
        action_key=action_key,
    )
    if not outcome.handled:
        django_messages.error(request, f"Azione non applicata: {outcome.reply_text or 'non supportata'}")
        return redirect("/archibald-mail/inbox/")

    row.selected_action_key = outcome.action_key
    row.classification_label = (category or outcome.action_key)[:80]
    row.review_notes = notes[:3000]
    row.review_status = ArchibaldEmailMessage.ReviewStatus.APPLIED
    row.reviewed_at = timezone.now()
    row.save(
        update_fields=[
            "selected_action_key",
            "classification_label",
            "review_notes",
            "review_status",
            "reviewed_at",
            "updated_at",
        ]
    )
    django_messages.success(request, outcome.reply_text or "Azione applicata.")
    return redirect("/archibald-mail/inbox/")


@login_required
def ignore_inbound_message(request, message_id: int):
    if request.method != "POST":
        return redirect("/archibald-mail/inbox/")
    row = get_object_or_404(
        ArchibaldEmailMessage,
        id=message_id,
        owner=request.user,
        direction=ArchibaldEmailMessage.Direction.INBOUND,
    )
    row.review_status = ArchibaldEmailMessage.ReviewStatus.IGNORED
    row.reviewed_at = timezone.now()
    row.review_notes = (request.POST.get("review_notes") or row.review_notes or "").strip()[:3000]
    row.classification_label = (request.POST.get("classification_label") or row.classification_label or "").strip()[:80]
    row.save(update_fields=["review_status", "reviewed_at", "review_notes", "classification_label", "updated_at"])
    django_messages.success(request, "Email marcata come ignorata.")
    return redirect("/archibald-mail/inbox/")


@login_required
def reopen_inbound_message(request, message_id: int):
    if request.method != "POST":
        return redirect("/archibald-mail/inbox/")
    row = get_object_or_404(
        ArchibaldEmailMessage,
        id=message_id,
        owner=request.user,
        direction=ArchibaldEmailMessage.Direction.INBOUND,
    )
    row.review_status = ArchibaldEmailMessage.ReviewStatus.PENDING
    row.reviewed_at = None
    row.save(update_fields=["review_status", "reviewed_at", "updated_at"])
    django_messages.success(request, "Email riportata in stato pending.")
    return redirect("/archibald-mail/inbox/")
