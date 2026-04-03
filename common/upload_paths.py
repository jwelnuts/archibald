from pathlib import PurePosixPath
from uuid import uuid4

from django.utils import timezone


def _user_segment(instance):
    owner_id = getattr(instance, "owner_id", None) or getattr(getattr(instance, "owner", None), "id", None)
    if owner_id is None:
        return "user/anonymous"
    return f"user/{owner_id}"


def _build_upload_path(instance, base_dir, filename):
    original_name = PurePosixPath(filename or "").name
    extension = PurePosixPath(original_name).suffix.lower()
    stamp = timezone.now()
    unique_name = f"{uuid4().hex}{extension}"
    return str(PurePosixPath(base_dir) / _user_segment(instance) / stamp.strftime("%Y/%m") / unique_name)


def contact_profile_image_upload_to(instance, filename):
    return _build_upload_path(instance, "contacts/profile_images", filename)


def project_note_attachment_upload_to(instance, filename):
    return _build_upload_path(instance, "projects/notes", filename)


def transaction_attachment_upload_to(instance, filename):
    return _build_upload_path(instance, "transactions/attachments", filename)
