import re

APP_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
MODEL_RE = re.compile(r"^[A-Z][A-Za-z0-9]{1,39}$")
SUPPORTED_FIELD_KINDS = {"char", "text", "integer", "decimal", "date", "datetime", "boolean", "choice"}