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


def _extract_conversation_id(data) -> str:
    if not isinstance(data, dict):
        return ""
    value = data.get("conversation")
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("id") or "")
    return ""


def _extract_response_id(data) -> str:
    if isinstance(data, dict):
        return str(data.get("id") or "")
    return ""


def _resolve_model() -> str:
    return (
        os.getenv("OPENAI_MODEL_ARCHIBALD", "").strip()
        or os.getenv("OPENAI_MODEL", "").strip()
        or "gpt-5.4"
    )


def _resolve_reasoning_effort(model: str) -> str:
    configured = (
        os.getenv("ARCHIBALD_REASONING_EFFORT", "").strip().lower()
        or os.getenv("OPENAI_REASONING_EFFORT", "").strip().lower()
    )
    if configured:
        return configured
    if model.startswith("gpt-5"):
        return "high"
    return ""


def _post_json(url: str, payload: dict, api_key: str, timeout: int = 60) -> tuple[dict, int]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = getattr(resp, "status", 200)
        data = json.loads(resp.read().decode("utf-8"))
    return data, status


def create_openai_conversation_with_debug():
    api_key = os.getenv("OPENAI_API_KEY", "")
    debug = {
        "provider": "openai",
        "api_key_configured": bool(api_key),
        "operation": "create_conversation",
        "status": "pending",
    }

    if not api_key:
        debug["status"] = "config_error"
        debug["error"] = "OPENAI_API_KEY non configurata."
        return "", debug

    started_at = time.monotonic()
    try:
        data, status = _post_json("https://api.openai.com/v1/conversations", {}, api_key)
        debug["http_status"] = status
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else ""
        debug["status"] = "http_error"
        debug["http_status"] = exc.code
        debug["duration_ms"] = int((time.monotonic() - started_at) * 1000)
        debug["error"] = f"Errore API: {exc}"
        if detail:
            debug["error_detail"] = detail[:2000]
        return "", debug
    except Exception as exc:
        debug["status"] = "runtime_error"
        debug["duration_ms"] = int((time.monotonic() - started_at) * 1000)
        debug["error"] = f"Errore API: {exc}"
        return "", debug

    conversation_id = str(data.get("id") or "") if isinstance(data, dict) else ""
    if not conversation_id:
        debug["status"] = "runtime_error"
        debug["duration_ms"] = int((time.monotonic() - started_at) * 1000)
        debug["error"] = "ID conversazione non presente nella risposta."
        return "", debug

    debug["status"] = "ok"
    debug["duration_ms"] = int((time.monotonic() - started_at) * 1000)
    debug["conversation_id"] = conversation_id
    return conversation_id, debug


def request_openai_response_with_state(
    messages,
    instructions: str,
    *,
    conversation_id: str = "",
    previous_response_id: str = "",
    metadata: dict | None = None,
):
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = _resolve_model()
    reasoning_effort = _resolve_reasoning_effort(model)
    use_conversation = bool(conversation_id)
    use_previous_response = bool(previous_response_id) and not use_conversation

    debug = {
        "provider": "openai",
        "model": model,
        "api_key_configured": bool(api_key),
        "messages_count": len(messages or []),
        "instruction_chars": len(instructions or ""),
        "conversation_id_in": conversation_id or "",
        "previous_response_id_in": previous_response_id or "",
        "status": "pending",
    }

    if not api_key:
        debug["status"] = "config_error"
        debug["error"] = "OPENAI_API_KEY non configurata."
        state = {"conversation_id": conversation_id or "", "response_id": "", "model": model}
        return "OPENAI_API_KEY non configurata.", debug, state

    payload = {
        "model": model,
        "instructions": instructions,
        "input": messages,
        "store": True,
    }
    if use_conversation:
        payload["conversation"] = conversation_id
    elif use_previous_response:
        payload["previous_response_id"] = previous_response_id
    if reasoning_effort:
        payload["reasoning"] = {"effort": reasoning_effort}
    if isinstance(metadata, dict) and metadata:
        payload["metadata"] = metadata

    debug["request_preview"] = {
        "input_roles": [msg.get("role") for msg in messages or []],
        "uses_conversation": use_conversation,
        "uses_previous_response_id": use_previous_response,
        "reasoning_effort": reasoning_effort or "",
    }

    started_at = time.monotonic()
    data = None
    try:
        data, status = _post_json("https://api.openai.com/v1/responses", payload, api_key)
        debug["http_status"] = status
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else ""
        # Retry once without reasoning if the selected model rejects reasoning settings.
        if reasoning_effort and exc.code == 400 and "reasoning" in detail.lower():
            payload.pop("reasoning", None)
            debug["reasoning_fallback"] = "retry_without_reasoning"
            try:
                data, status = _post_json("https://api.openai.com/v1/responses", payload, api_key)
                debug["http_status"] = status
            except urllib.error.HTTPError as retry_exc:
                retry_detail = retry_exc.read().decode("utf-8") if retry_exc.fp else ""
                debug["status"] = "http_error"
                debug["http_status"] = retry_exc.code
                debug["duration_ms"] = int((time.monotonic() - started_at) * 1000)
                debug["error"] = f"Errore API: {retry_exc}"
                if retry_detail:
                    debug["error_detail"] = retry_detail[:2000]
                state = {"conversation_id": conversation_id or "", "response_id": "", "model": model}
                return f"Errore API: {retry_exc} {retry_detail}", debug, state
            except Exception as retry_exc:
                debug["status"] = "runtime_error"
                debug["duration_ms"] = int((time.monotonic() - started_at) * 1000)
                debug["error"] = f"Errore API: {retry_exc}"
                state = {"conversation_id": conversation_id or "", "response_id": "", "model": model}
                return f"Errore API: {retry_exc}", debug, state
        else:
            debug["status"] = "http_error"
            debug["http_status"] = exc.code
            debug["duration_ms"] = int((time.monotonic() - started_at) * 1000)
            debug["error"] = f"Errore API: {exc}"
            if detail:
                debug["error_detail"] = detail[:2000]
            state = {"conversation_id": conversation_id or "", "response_id": "", "model": model}
            return f"Errore API: {exc} {detail}", debug, state
    except Exception as exc:
        debug["status"] = "runtime_error"
        debug["duration_ms"] = int((time.monotonic() - started_at) * 1000)
        debug["error"] = f"Errore API: {exc}"
        state = {"conversation_id": conversation_id or "", "response_id": "", "model": model}
        return f"Errore API: {exc}", debug, state

    response_text = _extract_output_text(data)
    response_id = _extract_response_id(data)
    response_conversation_id = _extract_conversation_id(data) or (conversation_id or "")
    state = {
        "conversation_id": response_conversation_id,
        "response_id": response_id,
        "model": model,
    }

    debug["status"] = "ok"
    debug["duration_ms"] = int((time.monotonic() - started_at) * 1000)
    debug["response_chars"] = len(response_text or "")
    debug["response_id"] = response_id
    debug["conversation_id"] = response_conversation_id
    if isinstance(data, dict):
        debug["response_keys"] = list(data.keys())
    return response_text, debug, state


def request_openai_response_with_debug(messages, instructions: str):
    response_text, debug, _ = request_openai_response_with_state(messages, instructions)
    return response_text, debug


def request_openai_response(messages, instructions: str) -> str:
    response_text, _ = request_openai_response_with_debug(messages, instructions)
    return response_text
