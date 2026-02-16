from __future__ import annotations

from typing import Any

from django.db import transaction

from .models import DebugChangeLog
from .middleware import is_debug_middleware_enabled


def log_change(
    *,
    user=None,
    source: str = "",
    action: str = DebugChangeLog.Action.UPDATE,
    app_label: str = "",
    model_name: str = "",
    object_id: str = "",
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    note: str = "",
) -> None:
    """
    Registra una modifica solo se il middleware debug e attivo.
    Se il middleware non e caricato, la funzione non fa nulla.
    """
    if not is_debug_middleware_enabled():
        return

    def _create_log() -> None:
        DebugChangeLog.objects.create(
            user=user,
            source=source,
            action=action,
            app_label=app_label,
            model_name=model_name,
            object_id=str(object_id) if object_id else "",
            before=before,
            after=after,
            note=note,
        )

    transaction.on_commit(_create_log)
