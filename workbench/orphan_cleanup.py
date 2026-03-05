from __future__ import annotations

import re
import shutil
from dataclasses import dataclass

from django.conf import settings
from django.core.management.base import CommandError

from .app_builder import project_settings_path, project_urls_path
from .models import DebugChangeLog


APP_LABEL_RE = re.compile(r"^[a-z][a-z0-9_]{1,39}$")


@dataclass
class OrphanCleanupResult:
    app_label: str
    dry_run: bool
    settings_removed: int
    urls_removed: int
    logs_deleted: int
    app_dir_deleted: bool


def remove_app_from_settings_text(source: str, app_label: str) -> tuple[str, int]:
    pattern = re.compile(rf"^\s*['\"]{re.escape(app_label)}['\"],\s*$")
    removed = 0
    kept: list[str] = []
    for line in source.splitlines(keepends=True):
        if pattern.match(line):
            removed += 1
            continue
        kept.append(line)
    return "".join(kept), removed


def remove_app_from_urls_text(source: str, app_label: str) -> tuple[str, int]:
    pattern = re.compile(
        rf"^\s*path\(\s*['\"]{re.escape(app_label)}/['\"]\s*,\s*include\(\s*['\"]{re.escape(app_label)}\.urls['\"]\s*\)\s*\)\s*,\s*$"
    )
    removed = 0
    kept: list[str] = []
    for line in source.splitlines(keepends=True):
        if pattern.match(line):
            removed += 1
            continue
        kept.append(line)
    return "".join(kept), removed


def cleanup_generated_app(
    app_label: str,
    *,
    dry_run: bool = False,
    keep_logs: bool = False,
    all_logs: bool = False,
    skip_settings: bool = False,
    skip_urls: bool = False,
    remove_dir: bool = False,
) -> OrphanCleanupResult:
    app_label = (app_label or "").strip()
    if not APP_LABEL_RE.match(app_label):
        raise CommandError("app_label non valido. Usa minuscole, numeri e underscore (es: fileholder).")

    settings_removed = 0
    urls_removed = 0
    logs_deleted = 0
    app_dir_deleted = False

    if not skip_settings:
        settings_path = project_settings_path()
        current = settings_path.read_text(encoding="utf-8")
        updated, settings_removed = remove_app_from_settings_text(current, app_label)
        if settings_removed and not dry_run:
            if not updated.endswith("\n"):
                updated += "\n"
            settings_path.write_text(updated, encoding="utf-8")

    if not skip_urls:
        urls_path = project_urls_path()
        current = urls_path.read_text(encoding="utf-8")
        updated, urls_removed = remove_app_from_urls_text(current, app_label)
        if urls_removed and not dry_run:
            if not updated.endswith("\n"):
                updated += "\n"
            urls_path.write_text(updated, encoding="utf-8")

    if not keep_logs:
        logs_qs = DebugChangeLog.objects.filter(app_label=app_label)
        if not all_logs:
            logs_qs = logs_qs.filter(source="workbench.ai_app_generator")
        logs_deleted = logs_qs.count()
        if logs_deleted and not dry_run:
            logs_qs.delete()

    if remove_dir:
        app_dir = settings.BASE_DIR / app_label
        if app_dir.exists():
            if not app_dir.is_dir():
                raise CommandError(f"Percorso non valido (non directory): {app_dir}")
            if not dry_run:
                shutil.rmtree(app_dir)
            app_dir_deleted = True

    return OrphanCleanupResult(
        app_label=app_label,
        dry_run=dry_run,
        settings_removed=settings_removed,
        urls_removed=urls_removed,
        logs_deleted=logs_deleted,
        app_dir_deleted=app_dir_deleted,
    )
