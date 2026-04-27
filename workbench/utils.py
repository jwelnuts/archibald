import re
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings

APP_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
MODEL_RE = re.compile(r"^[A-Z][A-Za-z0-9]{1,39}$")


class AppBuilderError(Exception):
    """Errore controllato durante la generazione di una app Django."""


@dataclass
class FieldSpec:
    name: str
    kind: str
    required: bool = False
    choices: list[str] = field(default_factory=list)


@dataclass
class AppSpec:
    app_title: str
    model_name: str
    model_plural: str
    description: str
    fields: list[FieldSpec]


@dataclass
class SetupCommandResult:
    command: str
    ok: bool
    output: str
    return_code: int


def _run_manage_command(args: list[str], timeout_seconds: int = 180) -> SetupCommandResult:
    manage_path = settings.BASE_DIR / "manage.py"
    display = f"{Path(sys.executable).name} manage.py {' '.join(args)}"
    command = [sys.executable, str(manage_path), *args]

    try:
        completed = subprocess.run(
            command,
            cwd=settings.BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        output = (completed.stdout or "").strip() or "(nessun output)"
        return SetupCommandResult(
            command=display,
            ok=completed.returncode == 0,
            output=output,
            return_code=completed.returncode,
        )
    except subprocess.TimeoutExpired as exc:
        timeout_output = (exc.stdout or "").strip() if isinstance(exc.stdout, str) else ""
        output = (timeout_output + "\nTimeout durante l'esecuzione del comando.").strip()
        return SetupCommandResult(
            command=display,
            ok=False,
            output=output or "Timeout durante l'esecuzione del comando.",
            return_code=124,
        )
    except OSError as exc:
        return SetupCommandResult(
            command=display,
            ok=False,
            output=f"Errore esecuzione comando: {exc}",
            return_code=127,
        )


def normalize_app_name(raw_name: str) -> str:
    name = (raw_name or "").strip().lower().replace("-", "_")
    name = re.sub(r"[^a-z0-9_]", "", name)
    if not APP_NAME_RE.match(name):
        raise AppBuilderError(
            "Nome app non valido. Usa solo lettere minuscole, numeri e underscore (es: report_builder)."
        )
    if keyword.iskeyword(name):
        raise AppBuilderError("Il nome app coincide con una keyword Python.")

    installed_labels = {entry.split(".")[-1] for entry in settings.INSTALLED_APPS}
    if name in installed_labels:
        raise AppBuilderError(f"L'app '{name}' e gia presente in INSTALLED_APPS.")

    return name


def extract_output_text(data: dict) -> str:
    if not isinstance(data, dict):
        return ""
    direct = data.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    for item in data.get("output", []):
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        for block in item.get("content", []):
            if not isinstance(block, dict):
                continue
            if block.get("type") in {"output_text", "text"}:
                text = block.get("text", "")
                if isinstance(text, str) and text.strip():
                    return text.strip()
    return ""


def sanitize_model_name(raw_name: str) -> str:
    if MODEL_RE.match(raw_name):
        return raw_name
    cleaned = re.sub(r"[^A-Za-z0-9]", "", raw_name)
    if not cleaned:
        return "Item"
    repaired = cleaned[0].upper() + cleaned[1:]
    if not MODEL_RE.match(repaired):
        return "Item"
    return repaired


def snake_to_pascal(name: str) -> str:
    parts = [chunk for chunk in name.replace("-", "_").split("_") if chunk]
    if not parts:
        return "Item"
    return "".join(chunk[:1].upper() + chunk[1:] for chunk in parts)