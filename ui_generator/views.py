import json
import os
import urllib.error
import urllib.request

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dashboard(request):
    context = {"gpt_response": None, "gpt_error": None, "gpt_prompt": ""}

    if request.method == "POST":
        prompt = (request.POST.get("gpt_prompt") or "").strip()
        context["gpt_prompt"] = prompt

        if not prompt:
            context["gpt_error"] = "Inserisci una richiesta valida."
            return render(request, "ui_generator/dashboard.html", context)

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            context["gpt_error"] = "OPENAI_API_KEY non configurata nell'ambiente."
            return render(request, "ui_generator/dashboard.html", context)

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        payload = {
            "model": model,
            "instructions": (
                "Sei un generatore di UI. Rispondi solo con JSON valido "
                "e nessun testo extra."
            ),
            "input": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }

        req = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw)
                context["gpt_response"] = json.dumps(
                    data, indent=2, ensure_ascii=False
                )
        except urllib.error.HTTPError as exc:
            try:
                error_body = exc.read().decode("utf-8")
            except Exception:
                error_body = ""
            context["gpt_error"] = (
                f"Errore API OpenAI ({exc.code}). {error_body}"
            ).strip()
        except urllib.error.URLError as exc:
            context["gpt_error"] = f"Errore di rete: {exc.reason}"
        except json.JSONDecodeError:
            context["gpt_error"] = "Risposta non JSON valida."
        except Exception as exc:
            context["gpt_error"] = f"Errore inatteso: {exc}"

    return render(request, "ui_generator/dashboard.html", context)
