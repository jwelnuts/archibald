from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.dav import (
    DavProvisioningError,
    default_user_collection_slug,
    ensure_user_default_collection,
    sync_radicale_users_file,
)
from core.models import DavAccount


class Command(BaseCommand):
    help = "Sincronizza il file utenti htpasswd usato da Radicale."

    def handle(self, *args, **options):
        if not settings.CALDAV_ENABLED:
            self.stdout.write(self.style.WARNING("CALDAV_ENABLED=false: sincronizzazione Radicale saltata."))
            return

        try:
            sync_radicale_users_file()
        except DavProvisioningError as exc:
            raise CommandError(str(exc)) from exc

        target_slug = default_user_collection_slug()
        migrated = 0
        processed = 0
        for dav_username in DavAccount.objects.filter(is_active=True).values_list("dav_username", flat=True):
            try:
                _dir, _props, moved_legacy = ensure_user_default_collection(
                    principal=dav_username,
                    calendar_slug=target_slug,
                    legacy_slug="calendario",
                )
            except DavProvisioningError as exc:
                raise CommandError(
                    f"Sync utenti completata, ma default collection non creata per '{dav_username}': {exc}"
                ) from exc
            processed += 1
            if moved_legacy:
                migrated += 1

        self.stdout.write(self.style.SUCCESS("File utenti Radicale sincronizzato."))
        self.stdout.write(
            self.style.SUCCESS(
                f"Collection personali default allineate ({target_slug}): utenti={processed}, migrate={migrated}."
            )
        )
