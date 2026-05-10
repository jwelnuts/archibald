import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from .settings import *  # noqa

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

MIGRATION_MODULES = {app.split(".")[-1]: None for app in INSTALLED_APPS}
