# LLMVault Live Mode — model discovery.  Made by CyberSunil.  (c) 2026 CyberSunil.  MIT License.
"""Single source of truth for "what can this player actually talk to right now".

Both the startup terminal banner and the in-chat model dropdown read from
`discover()`. That is the whole point of this module existing: if they each did
their own detection they would eventually disagree, and the player would see a
dropdown offering a model the server can't reach.

Provider support is intentionally staged. Ollama is the supported path today.
The OpenAI-compatible branch is wired but stays hidden unless a key is present,
because adversarial testing against a commercial endpoint is a usage-policy
question for whoever owns the key, not something to switch on by default.
"""
from __future__ import annotations

import config
from . import ollama_client


def _pretty(name: str) -> str:
    """'qwen2.5:3b-instruct' -> 'Qwen2.5 3B Instruct (local)'."""
    base = name.split(":")[0].replace("-", " ").replace(".", ".")
    tag = name.split(":")[1] if ":" in name else ""
    label = base.title()
    if tag:
        label += " " + tag.replace("-", " ").upper() if len(tag) <= 4 else " " + tag.replace("-", " ").title()
    return f"{label} (local)"


def discover() -> dict:
    """Probe every configured provider. Never raises; always returns a dict.

    Shape:
      {
        "ollama":  {"available": bool, "host": str, "models": [str], "error": str|None},
        "openai":  {"available": bool, "configured": bool},
        "models":  [{"id","provider","label"}],   # flat list for the dropdown
        "ready":   bool,                            # any usable model anywhere
      }
    """
    host = getattr(config, "OLLAMA_HOST", "http://localhost:11434")
    up = ollama_client.is_available(host)
    names = ollama_client.list_models(host) if up else []

    models = [{"id": n, "provider": "ollama", "label": _pretty(n)} for n in names]

    openai_key = getattr(config, "OPENAI_API_KEY", None)
    openai_on = bool(openai_key)
    if openai_on:
        for mid in getattr(config, "OPENAI_MODELS", ["gpt-4o-mini"]):
            models.append({"id": mid, "provider": "openai",
                           "label": f"{mid} (your API key)"})

    return {
        "ollama": {
            "available": up,
            "host": host,
            "models": names,
            "error": None if up else f"No Ollama server responding at {host}",
        },
        "openai": {"available": openai_on, "configured": openai_on},
        "models": models,
        "ready": bool(models),
    }


def default_model(info: dict | None = None) -> str | None:
    """Preferred model to select in the dropdown.

    Prefers the model the scenario prompts were tuned against (config
    OLLAMA_DEFAULT_MODEL) when the player actually has it pulled; otherwise
    falls back to whatever is available rather than offering nothing.
    """
    info = info or discover()
    want = getattr(config, "OLLAMA_DEFAULT_MODEL", None)
    ids = [m["id"] for m in info["models"]]
    if want and want in ids:
        return want
    # tolerate tag drift: 'qwen2.5:3b-instruct' vs 'qwen2.5:3b'
    if want:
        stem = want.split(":")[0]
        for mid in ids:
            if mid.split(":")[0] == stem:
                return mid
    return ids[0] if ids else None


def startup_banner() -> str:
    """The text printed to the terminal on `python app.py`.

    Doubles as ops output and as the setup instruction: a player who hasn't
    installed Ollama learns it here, before opening a browser tab.
    """
    info = discover()
    lines = ["", f"  {config.APP_NAME} — Live Mode preflight"]
    o = info["ollama"]
    if o["available"]:
        n = len(o["models"])
        lines.append(f"    Ollama    : detected at {o['host']}  ({n} model{'s' if n != 1 else ''})")
        for m in o["models"][:6]:
            lines.append(f"                  - {m}")
        if n > 6:
            lines.append(f"                  … and {n - 6} more")
        if n == 0:
            lines.append("                  (no models pulled — try: ollama pull qwen2.5:3b-instruct)")
    else:
        lines.append(f"    Ollama    : not detected at {o['host']}")
        lines.append("                  Live Mode will show setup instructions instead of labs.")
        lines.append("                  Install: https://ollama.com  then: ollama pull qwen2.5:3b-instruct")
    lines.append(f"    OpenAI    : {'configured' if info['openai']['configured'] else 'not configured (optional; set OPENAI_API_KEY)'}")
    lines.append(f"    Live Mode : {'READY' if info['ready'] else 'unavailable (Play Mode is unaffected)'}")
    lines.append("")
    return "\n".join(lines)
