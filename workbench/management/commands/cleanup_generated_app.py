from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from workbench.orphan_cleanup import APP_LABEL_RE, cleanup_generated_app


class Command(BaseCommand):
    help = (
        "Pulisce una app generata orfana dal Workbench: "
        "rimuove log di build, riferimenti in settings/urls e opzionalmente la cartella app."
    )

    def add_arguments(self, parser):
        parser.add_argument("app_label", help="Nome tecnico app (es: fileholder)")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra cosa verrebbe cambiato senza salvare modifiche.",
        )
        parser.add_argument(
            "--keep-logs",
            action="store_true",
            help="Non eliminare log da workbench_debugchangelog.",
        )
        parser.add_argument(
            "--all-logs",
            action="store_true",
            help="Elimina tutti i log con app_label (non solo quelli da ai_app_generator).",
        )
        parser.add_argument(
            "--skip-settings",
            action="store_true",
            help="Non rimuovere entry da INSTALLED_APPS.",
        )
        parser.add_argument(
            "--skip-urls",
            action="store_true",
            help="Non rimuovere route da project urls.",
        )
        parser.add_argument(
            "--remove-dir",
            action="store_true",
            help="Elimina anche la cartella app se presente in BASE_DIR.",
        )

    def handle(self, *args, **options):
        app_label: str = (options["app_label"] or "").strip()
        dry_run = bool(options["dry_run"])
        keep_logs = bool(options["keep_logs"])
        all_logs = bool(options["all_logs"])
        skip_settings = bool(options["skip_settings"])
        skip_urls = bool(options["skip_urls"])
        remove_dir = bool(options["remove_dir"])

        if not APP_LABEL_RE.match(app_label):
            raise CommandError("app_label non valido. Usa minuscole, numeri e underscore (es: fileholder).")

        self.stdout.write(self.style.NOTICE(f"[cleanup] app_label={app_label} dry_run={dry_run}"))

        result = cleanup_generated_app(
            app_label=app_label,
            dry_run=dry_run,
            keep_logs=keep_logs,
            all_logs=all_logs,
            skip_settings=skip_settings,
            skip_urls=skip_urls,
            remove_dir=remove_dir,
        )

        self.stdout.write(f"INSTALLED_APPS entries rimosse: {result.settings_removed}")
        self.stdout.write(f"URL routes rimosse: {result.urls_removed}")
        if keep_logs:
            self.stdout.write("Log: mantenuti (--keep-logs).")
        else:
            self.stdout.write(f"Log eliminati: {result.logs_deleted}")
        if remove_dir:
            self.stdout.write(f"Cartella app eliminata: {'si' if result.app_dir_deleted else 'no'}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run completato: nessuna modifica salvata."))
        else:
            self.stdout.write(self.style.SUCCESS("Cleanup completato."))
