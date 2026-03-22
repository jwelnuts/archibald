from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.dav import (
    DavProvisioningError,
    default_user_collection_slug,
    ensure_user_default_collection,
)
from core.models import DavAccount


class Command(BaseCommand):
    help = (
        "Garantisce la collection DAV personale di default per ogni utente DAV "
        "e migra la legacy collection (es. 'calendario') quando presente."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            action="append",
            dest="usernames",
            default=[],
            help="Username DAV da processare (ripetibile). Se omesso, processa tutti gli account attivi.",
        )
        parser.add_argument(
            "--target-slug",
            dest="target_slug",
            default="",
            help="Slug collection target (default: CALDAV_DEFAULT_USER_COLLECTION).",
        )
        parser.add_argument(
            "--legacy-slug",
            dest="legacy_slug",
            default="calendario",
            help="Slug legacy da migrare se presente (default: calendario).",
        )

    def handle(self, *args, **options):
        if not settings.CALDAV_ENABLED:
            self.stdout.write(self.style.WARNING("CALDAV_ENABLED=false: comando saltato."))
            return

        target_slug = (options.get("target_slug") or "").strip() or default_user_collection_slug()
        legacy_slug = (options.get("legacy_slug") or "").strip() or "calendario"
        usernames = [item.strip() for item in (options.get("usernames") or []) if item and item.strip()]

        accounts = DavAccount.objects.filter(is_active=True).order_by("dav_username")
        if usernames:
            accounts = accounts.filter(dav_username__in=usernames)

        if not accounts.exists():
            self.stdout.write(self.style.WARNING("Nessun account DAV attivo da processare."))
            return

        processed = 0
        migrated = 0
        errors = 0

        for account in accounts:
            try:
                _dir, _props, moved_legacy = ensure_user_default_collection(
                    principal=account.dav_username,
                    calendar_slug=target_slug,
                    legacy_slug=legacy_slug,
                )
            except DavProvisioningError as exc:
                errors += 1
                self.stderr.write(
                    self.style.ERROR(f"[ERR] {account.dav_username}: {exc}")
                )
                continue

            processed += 1
            if moved_legacy:
                migrated += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[MIGRATED] {account.dav_username}: {legacy_slug} -> {target_slug}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[OK] {account.dav_username}: {target_slug}"
                    )
                )

        summary = (
            f"Processati={processed} | Migrati={migrated} | Errori={errors} | "
            f"Target={target_slug} | Legacy={legacy_slug}"
        )
        if errors:
            raise CommandError(summary)
        self.stdout.write(self.style.SUCCESS(summary))
