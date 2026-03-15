import os
import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from archibald_mail.models import ArchibaldMailboxConfig
from archibald_mail.services import process_inbox_for_all, process_inbox_for_config


def _default_poll_seconds() -> int:
    raw = (os.getenv("ARCHIBALD_MAIL_POLL_SECONDS") or "").strip()
    if raw.isdigit():
        return max(30, int(raw))
    return 300


class Command(BaseCommand):
    help = "Worker inbox Archibald: processa email a intervallo costante (default 300s)."

    def add_arguments(self, parser):
        parser.add_argument("--interval-seconds", type=int, default=_default_poll_seconds())
        parser.add_argument("--limit", type=int, default=0, help="Override limite email per run (0 = default config).")
        parser.add_argument("--user", help="Username o email dell'utente (opzionale).")
        parser.add_argument("--force", action="store_true", help="Ignora flag is_enabled.")
        parser.add_argument("--run-once", action="store_true", help="Esegue un solo ciclo e termina.")

    def _resolve_user_config(self, user_value: str) -> ArchibaldMailboxConfig:
        User = get_user_model()
        user = User.objects.filter(username=user_value).first() or User.objects.filter(email=user_value).first()
        if not user:
            raise CommandError(f"Utente non trovato: {user_value}")
        config = ArchibaldMailboxConfig.objects.filter(owner=user).first()
        if not config:
            raise CommandError(f"Configurazione Archibald Mail mancante per utente: {user_value}")
        return config

    def _run_cycle(self, *, limit: int | None, user_value: str, force: bool) -> tuple[int, int, int, int, int]:
        fetched_total = 0
        processed_total = 0
        replied_total = 0
        skipped_total = 0
        failed_total = 0

        if user_value:
            config = self._resolve_user_config(user_value)
            result = process_inbox_for_config(config, limit=limit, force=force)
            fetched_total += result.get("fetched", 0)
            processed_total += result.get("processed", 0)
            replied_total += result.get("replied", 0)
            skipped_total += result.get("skipped", 0)
            failed_total += result.get("failed", 0)
            self.stdout.write(
                f"[{config.owner.username}] fetched={result.get('fetched')} processed={result.get('processed')} "
                f"replied={result.get('replied')} skipped={result.get('skipped')} "
                f"failed={result.get('failed')} status={result.get('status')}"
            )
            return fetched_total, processed_total, replied_total, skipped_total, failed_total

        if force:
            rows = []
            for config in ArchibaldMailboxConfig.objects.select_related("owner"):
                try:
                    result = process_inbox_for_config(config, limit=limit, force=True)
                except Exception as exc:  # pragma: no cover - defensive logging path
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

        for config, result in rows:
            fetched_total += result.get("fetched", 0)
            processed_total += result.get("processed", 0)
            replied_total += result.get("replied", 0)
            skipped_total += result.get("skipped", 0)
            failed_total += result.get("failed", 0)
            self.stdout.write(
                f"[{config.owner.username}] fetched={result.get('fetched')} processed={result.get('processed')} "
                f"replied={result.get('replied')} skipped={result.get('skipped')} "
                f"failed={result.get('failed')} status={result.get('status')}"
            )

        if not rows:
            self.stdout.write("Nessuna configurazione Archibald Mail idonea trovata.")

        return fetched_total, processed_total, replied_total, skipped_total, failed_total

    def handle(self, *args, **options):
        interval = int(options.get("interval_seconds") or 300)
        if interval < 30:
            raise CommandError("--interval-seconds deve essere >= 30.")

        limit_value = int(options.get("limit") or 0)
        limit = limit_value or None
        user_value = (options.get("user") or "").strip()
        force = bool(options.get("force"))
        run_once = bool(options.get("run_once"))

        self.stdout.write(
            f"Archibald Mail worker avviato: interval={interval}s "
            f"limit={limit or 'default'} user={user_value or '-'} force={force} run_once={run_once}"
        )

        while True:
            cycle_start = timezone.now()
            fetched, processed, replied, skipped, failed = self._run_cycle(
                limit=limit,
                user_value=user_value,
                force=force,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"[cycle {cycle_start.isoformat()}] "
                    f"fetched={fetched} processed={processed} replied={replied} skipped={skipped} failed={failed}"
                )
            )

            if run_once:
                return

            elapsed = (timezone.now() - cycle_start).total_seconds()
            sleep_seconds = max(1, interval - int(elapsed))
            time.sleep(sleep_seconds)
