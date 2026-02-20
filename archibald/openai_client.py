import json
import os
import urllib.error
import urllib.request


def request_openai_response(messages, instructions: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return "OPENAI_API_KEY non configurata."

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "instructions": instructions,
        "input": messages,
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else ""
        return f"Errore API: {exc} {detail}"
    except Exception as exc:
        return f"Errore API: {exc}"

    if isinstance(data, dict):
        if data.get("output_text"):
            return data["output_text"]
        output = data.get("output", [])
        for item in output:
            if item.get("type") == "message":
                content = item.get("content", [])
                for block in content:
                    if block.get("type") in {"output_text", "text"}:
                        return block.get("text", "")
    return "Nessuna risposta disponibile."
