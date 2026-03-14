from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import redirect, render

from .forms import ArchibaldMailboxConfigForm, SendTestEmailForm
from .models import ArchibaldEmailMessage, ArchibaldMailboxConfig
from .services import (
    ArchibaldMailError,
    process_inbox_for_config,
    send_notification_for_config,
    send_test_email,
)


@login_required
def dashboard(request):
    config, _ = ArchibaldMailboxConfig.objects.get_or_create(owner=request.user)
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
        },
    )
