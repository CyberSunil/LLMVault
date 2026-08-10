# LLMVault Live Mode — Ollama HTTP client.  Made by CyberSunil.  (c) 2026 CyberSunil.  MIT License.
"""Minimal Ollama client built on the standard library.

Deliberately uses `urllib` rather than `requests` or the official `ollama`
package: Live Mode must not add dependencies to a project whose whole pitch is
"clone it and run it". Ollama's REST API is simple enough that the stdlib is
genuinely sufficient here.

Everything in this module fails soft. Ollama not installed, not running, model
not pulled, request timing out mid-stream — all surface as either a False/empty
return or an OllamaError the caller can render as a friendly message. Nothing
here should ever take the Flask app down.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Iterator


class OllamaError(RuntimeError):
    """Raised for any Ollama-side failure we want to show the player verbatim."""


def _post(host: str, path: str, payload: dict, timeout: float):
    req = urllib.request.Request(
        f"{host.rstrip('/')}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return urllib.request.urlopen(req, timeout=timeout)


def is_available(host: str, timeout: float = 1.5) -> bool:
    """True if an Ollama server answers on `host`. Never raises."""
    try:
        with urllib.request.urlopen(f"{host.rstrip('/')}/api/tags", timeout=timeout):
            return True
    except Exception:
        return False


def list_models(host: str, timeout: float = 3.0) -> list[str]:
    """Names of every model pulled locally, e.g. ['qwen2.5:3b-instruct'].

    Returns [] rather than raising when Ollama is down, so callers can treat
    "no Ollama" and "Ollama with no models" the same way: nothing to offer.
    """
    try:
        with urllib.request.urlopen(f"{host.rstrip('/')}/api/tags", timeout=timeout) as r:
            data = json.loads(r.read().decode())
    except Exception:
        return []
    return sorted(m.get("name", "") for m in data.get("models", []) if m.get("name"))


def chat_stream(host: str, model: str, messages: list[dict],
                timeout: float = 180.0, options: dict | None = None) -> Iterator[str]:
    """Yield reply text incrementally from Ollama's /api/chat.

    Streaming is not a nicety here. A 3B model on CPU produces roughly 5-20
    tokens/sec, so a synchronous request would leave the UI dead for 10-30
    seconds per turn. Yielding token-by-token keeps the lab feeling alive.

    The long default timeout is deliberate for the same reason: slow CPU
    inference is expected, not an error condition.
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": options or {"temperature": 0.8},
    }
    try:
        resp = _post(host, "/api/chat", payload, timeout)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:300]
        if e.code == 404:
            raise OllamaError(
                f"Model '{model}' is not pulled. Run:  ollama pull {model}") from e
        raise OllamaError(f"Ollama returned HTTP {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise OllamaError(
            f"Can't reach Ollama at {host}. Is it running?  ({e.reason})") from e
    except Exception as e:
        raise OllamaError(f"Ollama request failed: {e}") from e

    with resp:
        for raw in resp:
            line = raw.decode(errors="replace").strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue          # skip a malformed frame rather than abort the turn
            if chunk.get("error"):
                raise OllamaError(str(chunk["error"]))
            piece = (chunk.get("message") or {}).get("content", "")
            if piece:
                yield piece
            if chunk.get("done"):
                break
