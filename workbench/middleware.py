from __future__ import annotations

import threading


_debug_state = threading.local()


class DebugChangeLogMiddleware:
    """
    Abilita il logging dei cambiamenti per il Workbench.
    Carica questo middleware in settings.MIDDLEWARE quando vuoi attivarlo.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _debug_state.enabled = True
        try:
            response = self.get_response(request)
        finally:
            _debug_state.enabled = False
        return response


def is_debug_middleware_enabled() -> bool:
    return bool(getattr(_debug_state, "enabled", False))
