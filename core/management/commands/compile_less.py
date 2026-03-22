from pathlib import Path
import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Compila il file LESS globale in CSS per staticfiles (risolvendo gli import)."

    IMPORT_RE = re.compile(r'^\s*@import\s+(?:\([^)]+\)\s*)?["\']([^"\']+)["\']\s*;\s*$')

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default="",
            help="Percorso file LESS sorgente (default: core/static/core/styles.less).",
        )
        parser.add_argument(
            "--output",
            default="",
            help="Percorso file CSS destinazione (default: core/static/core/styles.css).",
        )
        parser.add_argument(
            "--minify",
            action="store_true",
            help="Attiva minificazione output CSS.",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Non stampare output informativo.",
        )

    def handle(self, *args, **options):
        source = Path(options["source"]) if options["source"] else settings.BASE_DIR / "core" / "static" / "core" / "styles.less"
        output = Path(options["output"]) if options["output"] else settings.BASE_DIR / "core" / "static" / "core" / "styles.css"

        if not source.exists():
            raise CommandError(f"File LESS sorgente non trovato: {source}")

        try:
            css_output = self._expand_imports(source)
        except Exception as exc:
            raise CommandError(f"Compilazione LESS fallita: {exc}") from exc

        if options["minify"]:
            css_output = self._minify_css(css_output)

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(css_output.rstrip() + "\n", encoding="utf-8")

        if not options["quiet"]:
            self.stdout.write(self.style.SUCCESS(f"LESS compilato: {source} -> {output}"))

    def _expand_imports(self, source: Path) -> str:
        visited_stack: list[Path] = []
        return self._expand_file(source.resolve(), visited_stack)

    def _expand_file(self, path: Path, visited_stack: list[Path]) -> str:
        if path in visited_stack:
            chain = " -> ".join(str(p) for p in [*visited_stack, path])
            raise CommandError(f"Ciclo di import individuato: {chain}")
        if not path.exists():
            raise CommandError(f"Import non trovato: {path}")

        visited_stack.append(path)
        chunks = [f"/* --- {path.relative_to(settings.BASE_DIR)} --- */\n"]
        for line in path.read_text(encoding="utf-8").splitlines():
            match = self.IMPORT_RE.match(line)
            if match:
                import_target = match.group(1)
                import_path = (path.parent / import_target).resolve()
                chunks.append(self._expand_file(import_path, visited_stack))
            else:
                chunks.append(line + "\n")
        visited_stack.pop()
        return "".join(chunks)

    def _minify_css(self, css_text: str) -> str:
        compact = re.sub(r"/\*[^*]*\*+(?:[^/*][^*]*\*+)*/", "", css_text)
        compact = re.sub(r"\s+", " ", compact)
        compact = re.sub(r"\s*([{}:;,])\s*", r"\1", compact)
        return compact.strip()
