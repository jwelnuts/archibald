from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.dav import DavProvisioningError, sync_radicale_users_file


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

        self.stdout.write(self.style.SUCCESS("File utenti Radicale sincronizzato."))
