from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from archibald_mail.models import ArchibaldMailboxConfig
from archibald_mail.services import send_due_notifications_for_all, send_notification_for_config


class Command(BaseCommand):
    help = "Invia notifiche email di Archibald basate su task/planner/subscriptions/routines."

    def add_arguments(self, parser):
        parser.add_argument("--user", help="Username o email dell'utente.")
        parser.add_argument("--force", action="store_true", help="Invia anche fuori orario e senza elementi in scadenza.")
        parser.add_argument(
            "--ignore-time-window",
            action="store_true",
            help="Non applica controllo orario, ma mantiene logica sent/skip.",
        )

    def handle(self, *args, **options):
        force = bool(options.get("force"))
        only_due = not bool(options.get("ignore_time_window"))

        if options.get("user"):
            user_value = options["user"].strip()
            User = get_user_model()
            user = User.objects.filter(username=user_value).first() or User.objects.filter(email=user_value).first()
            if not user:
                raise CommandError(f"Utente non trovato: {user_value}")

            config = ArchibaldMailboxConfig.objects.filter(owner=user).first()
            if not config:
                raise CommandError(f"Configurazione Archibald Mail mancante per utente: {user_value}")

            result = send_notification_for_config(config, force=force, only_due=only_due)
            msg = f"[{user.username}] sent={result.get('sent')} status={result.get('status')} reason={result.get('reason')}"
            if result.get("sent"):
                self.stdout.write(self.style.SUCCESS(msg))
            else:
                self.stdout.write(msg)
            return

        rows = send_due_notifications_for_all(force=force, only_due=only_due)
        if not rows:
            self.stdout.write("Nessuna configurazione notifiche trovata.")
            return

        for config, result in rows:
            msg = (
                f"[{config.owner.username}] sent={result.get('sent')} "
                f"status={result.get('status')} reason={result.get('reason')}"
            )
            if result.get("sent"):
                self.stdout.write(self.style.SUCCESS(msg))
            else:
                self.stdout.write(msg)
