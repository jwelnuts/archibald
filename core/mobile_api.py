from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse


class MobileApiCorsMiddleware:
    """Minimal CORS middleware for API endpoints (/api/*)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        if request.method == "OPTIONS":
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        origin = (request.headers.get("Origin") or "").strip()
        allowed_origin = self._allowed_origin(origin)
        if allowed_origin:
            response["Access-Control-Allow-Origin"] = allowed_origin
            response["Vary"] = "Origin"

        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        response["Access-Control-Max-Age"] = "600"
        return response

    def _allowed_origin(self, origin: str) -> str:
        if not origin:
            return ""

        allowed = [row.strip() for row in getattr(settings, "MOBILE_API_ALLOWED_ORIGINS", []) if row.strip()]
        if "*" in allowed:
            return "*"
        if origin in allowed:
            return origin
        return ""
