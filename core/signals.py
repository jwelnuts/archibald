import logging

from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .dav import DavProvisioningError, ensure_user_dav_access

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def sync_dav_on_login(sender, user, request, **kwargs):
    if not getattr(settings, "CALDAV_ENABLED", False):
        return
    if request is None or getattr(request, "_dav_synced", False):
        return

    raw_password = (request.POST.get("password") or "").strip()
    if not raw_password:
        return

    try:
        ensure_user_dav_access(user, raw_password=raw_password)
    except DavProvisioningError as exc:
        logger.warning("DAV sync failed during login for user=%s: %s", getattr(user, "id", None), exc)
    else:
        request._dav_synced = True
