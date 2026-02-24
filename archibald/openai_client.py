import json
import os
import time
import urllib.error
import urllib.request


def _extract_output_text(data) -> str:
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


def request_openai_response_with_debug(messages, instructions: str):
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    debug = {
        "provider": "openai",
        "model": model,
        "api_key_configured": bool(api_key),
        "messages_count": len(messages or []),
        "instruction_chars": len(instructions or ""),
        "status": "pending",
    }

    if not api_key:
        debug["status"] = "config_error"
        debug["error"] = "OPENAI_API_KEY non configurata."
        return "OPENAI_API_KEY non configurata.", debug

    payload = {
        "model": model,
        "instructions": instructions,
        "input": messages,
    }
    debug["request_preview"] = {
        "input_roles": [msg.get("role") for msg in messages or []],
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

    started_at = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            debug["http_status"] = getattr(resp, "status", 200)
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else ""
        debug["status"] = "http_error"
        debug["http_status"] = exc.code
        debug["duration_ms"] = int((time.monotonic() - started_at) * 1000)
        debug["error"] = f"Errore API: {exc}"
        if detail:
            debug["error_detail"] = detail[:2000]
        return f"Errore API: {exc} {detail}", debug
    except Exception as exc:
        debug["status"] = "runtime_error"
        debug["duration_ms"] = int((time.monotonic() - started_at) * 1000)
        debug["error"] = f"Errore API: {exc}"
        return f"Errore API: {exc}", debug

    response_text = _extract_output_text(data)
    debug["status"] = "ok"
    debug["duration_ms"] = int((time.monotonic() - started_at) * 1000)
    debug["response_chars"] = len(response_text or "")
    if isinstance(data, dict):
        debug["response_keys"] = list(data.keys())
    return response_text, debug


def request_openai_response(messages, instructions: str) -> str:
    response_text, _ = request_openai_response_with_debug(messages, instructions)
    return response_text
