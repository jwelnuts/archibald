from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from archibald_mail.models import ArchibaldMailboxConfig
from archibald_mail.services import process_inbox_for_all, process_inbox_for_config


class Command(BaseCommand):
    help = "Processa inbox IMAP di Archibald e invia risposte automatiche."

    def add_arguments(self, parser):
        parser.add_argument("--user", help="Username o email dell'utente.")
        parser.add_argument("--limit", type=int, default=0, help="Override limite email per run.")
        parser.add_argument("--force", action="store_true", help="Ignora flag is_enabled/auto_reply_enabled.")

    def handle(self, *args, **options):
        limit = options.get("limit") or None

        if options.get("user"):
            user_value = options["user"].strip()
            User = get_user_model()
            user = User.objects.filter(username=user_value).first() or User.objects.filter(email=user_value).first()
            if not user:
                raise CommandError(f"Utente non trovato: {user_value}")

            config = ArchibaldMailboxConfig.objects.filter(owner=user).first()
            if not config:
                raise CommandError(f"Configurazione Archibald Mail mancante per utente: {user_value}")

            result = process_inbox_for_config(config, limit=limit, force=bool(options.get("force")))
            self.stdout.write(
                self.style.SUCCESS(
                    f"[{user.username}] fetched={result['fetched']} replied={result['replied']} "
                    f"skipped={result['skipped']} failed={result['failed']} status={result['status']}"
                )
            )
            return

        if options.get("force"):
            rows = []
            for config in ArchibaldMailboxConfig.objects.select_related("owner"):
                try:
                    result = process_inbox_for_config(config, limit=limit, force=True)
                except Exception as exc:
                    result = {
                        "status": "error",
                        "fetched": 0,
                        "processed": 0,
                        "replied": 0,
                        "skipped": 0,
                        "failed": 1,
                        "errors": [str(exc)],
                    }
                rows.append((config, result))
        else:
            rows = process_inbox_for_all(limit=limit)

        if not rows:
            self.stdout.write("Nessuna configurazione idonea trovata.")
            return

        for config, result in rows:
            self.stdout.write(
                f"[{config.owner.username}] fetched={result['fetched']} replied={result['replied']} "
                f"skipped={result['skipped']} failed={result['failed']} status={result['status']}"
            )
