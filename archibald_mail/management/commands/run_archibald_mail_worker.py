import os
import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from archibald_mail.models import ArchibaldMailboxConfig
from archibald_mail.services import process_inbox_for_config


def _default_poll_seconds() -> int:
    raw = (os.getenv("ARCHIBALD_MAIL_POLL_SECONDS") or "").strip()
    if raw.isdigit():
        return max(30, int(raw))
    return 300


def _env_bool(name: str, *, default: bool) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def _default_archi_fast_enabled() -> bool:
    return _env_bool("ARCHIBALD_MAIL_ARCHI_FAST_ENABLED", default=True)


def _default_archi_fast_seconds() -> int:
    raw = (os.getenv("ARCHIBALD_MAIL_ARCHI_FAST_POLL_SECONDS") or "").strip()
    if raw.isdigit():
        return max(5, int(raw))
    return 5


def _default_archi_fast_limit() -> int:
    raw = (os.getenv("ARCHIBALD_MAIL_ARCHI_FAST_LIMIT") or "").strip()
    if raw.isdigit():
        return max(1, int(raw))
    return 3


class Command(BaseCommand):
    help = (
        "Worker inbox Archibald: ciclo standard a intervallo costante "
        "(default 300s) + corsia veloce per subject ARCHI (default 5s)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--interval-seconds", type=int, default=_default_poll_seconds())
        parser.add_argument("--limit", type=int, default=0, help="Override limite email per run (0 = default config).")
        parser.add_argument("--archi-fast-seconds", type=int, default=_default_archi_fast_seconds())
        parser.add_argument("--archi-fast-limit", type=int, default=_default_archi_fast_limit())
        parser.add_argument("--disable-archi-fast", action="store_true", help="Disattiva corsia veloce ARCHI.")
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

    def _iter_configs(self, *, user_value: str, force: bool):
        if user_value:
            yield self._resolve_user_config(user_value)
            return
        if force:
            rows = ArchibaldMailboxConfig.objects.select_related("owner").order_by("owner_id")
        else:
            rows = ArchibaldMailboxConfig.objects.filter(is_enabled=True).select_related("owner").order_by("owner_id")
        for row in rows:
            yield row

    def _run_cycle(
        self,
        *,
        limit: int | None,
        user_value: str,
        force: bool,
        search_criteria: tuple[str, ...] | None = None,
        cycle_label: str = "full",
    ) -> tuple[int, int, int, int, int]:
        fetched_total = 0
        processed_total = 0
        replied_total = 0
        skipped_total = 0
        failed_total = 0

        rows = []
        for config in self._iter_configs(user_value=user_value, force=force):
            try:
                result = process_inbox_for_config(
                    config,
                    limit=limit,
                    force=force,
                    search_criteria=search_criteria,
                )
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

        for config, result in rows:
            fetched_total += result.get("fetched", 0)
            processed_total += result.get("processed", 0)
            replied_total += result.get("replied", 0)
            skipped_total += result.get("skipped", 0)
            failed_total += result.get("failed", 0)
            self.stdout.write(
                f"[{cycle_label}:{config.owner.username}] fetched={result.get('fetched')} "
                f"processed={result.get('processed')} "
                f"replied={result.get('replied')} skipped={result.get('skipped')} "
                f"failed={result.get('failed')} status={result.get('status')}"
            )

        if not rows:
            self.stdout.write(f"Nessuna configurazione Archibald Mail idonea trovata ({cycle_label}).")

        return fetched_total, processed_total, replied_total, skipped_total, failed_total

    def handle(self, *args, **options):
        interval = int(options.get("interval_seconds") or 300)
        if interval < 30:
            raise CommandError("--interval-seconds deve essere >= 30.")

        limit_value = int(options.get("limit") or 0)
        limit = limit_value or None
        archi_fast_seconds = int(options.get("archi_fast_seconds") or _default_archi_fast_seconds())
        archi_fast_limit_value = int(options.get("archi_fast_limit") or _default_archi_fast_limit())
        archi_fast_limit = archi_fast_limit_value or None
        archi_fast_enabled = _default_archi_fast_enabled() and not bool(options.get("disable_archi_fast"))
        user_value = (options.get("user") or "").strip()
        force = bool(options.get("force"))
        run_once = bool(options.get("run_once"))

        if archi_fast_seconds < 5:
            raise CommandError("--archi-fast-seconds deve essere >= 5.")

        self.stdout.write(
            f"Archibald Mail worker avviato: interval={interval}s "
            f"limit={limit or 'default'} user={user_value or '-'} force={force} run_once={run_once} "
            f"archi_fast_enabled={archi_fast_enabled} "
            f"archi_fast_seconds={archi_fast_seconds} archi_fast_limit={archi_fast_limit or 'default'}"
        )

        archi_fast_search = ("UNSEEN", "SUBJECT", "ARCHI")

        if run_once:
            cycle_start = timezone.now()
            fetched, processed, replied, skipped, failed = self._run_cycle(
                limit=limit,
                user_value=user_value,
                force=force,
                cycle_label="full",
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"[cycle full {cycle_start.isoformat()}] "
                    f"fetched={fetched} processed={processed} replied={replied} skipped={skipped} failed={failed}"
                )
            )
            return

        next_full_cycle_at = time.monotonic()
        while True:
            current_tick = time.monotonic()
            if current_tick >= next_full_cycle_at:
                cycle_start = timezone.now()
                fetched, processed, replied, skipped, failed = self._run_cycle(
                    limit=limit,
                    user_value=user_value,
                    force=force,
                    cycle_label="full",
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[cycle full {cycle_start.isoformat()}] "
                        f"fetched={fetched} processed={processed} replied={replied} skipped={skipped} failed={failed}"
                    )
                )
                next_full_cycle_at = time.monotonic() + interval

            if archi_fast_enabled:
                fast_start = timezone.now()
                fetched, processed, replied, skipped, failed = self._run_cycle(
                    limit=archi_fast_limit,
                    user_value=user_value,
                    force=force,
                    search_criteria=archi_fast_search,
                    cycle_label="archi-fast",
                )
                if fetched or replied or failed:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"[cycle archi-fast {fast_start.isoformat()}] "
                            f"fetched={fetched} processed={processed} replied={replied} "
                            f"skipped={skipped} failed={failed}"
                        )
                    )
                time.sleep(archi_fast_seconds)
                continue

            sleep_seconds = max(1, int(next_full_cycle_at - time.monotonic()))
            time.sleep(sleep_seconds)
