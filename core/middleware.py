from __future__ import annotations

import logging
from threading import Lock

from django.conf import settings
from django.core.management import call_command


logger = logging.getLogger(__name__)


class DevLessCompileMiddleware:
    """
    In DEV mode compila styles.less ad ogni richiesta HTML GET
    per avere aggiornamenti immediati senza rebuild container.
    """

    _compile_lock = Lock()

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._must_compile(request):
            self._compile_less()
        return self.get_response(request)

    def _must_compile(self, request) -> bool:
        if not getattr(settings, "LESS_DEV_MODE", False):
            return False
        if request.method != "GET":
            return False
        if request.path.startswith("/static/"):
            return False
        accept = request.headers.get("Accept", "")
        return "text/html" in accept or "*/*" in accept

    def _compile_less(self) -> None:
        try:
            with self._compile_lock:
                call_command("compile_less", quiet=True)
        except Exception:
            logger.exception("Errore compilazione LESS in DevLessCompileMiddleware")
