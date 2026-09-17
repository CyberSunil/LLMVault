"""Global config for LLMVault."""

# --- Branding (single source of truth; changing these renames the whole app) ---
APP_NAME = "LLMVault"
APP_EMOJI = "🔐"

# Author credit. Baked in and shown on every page; there is no runtime path to
# change it (see app.py — no endpoint writes AUTHOR/COPYRIGHT).
AUTHOR = "CyberSunil"
COPYRIGHT_YEAR = "2026"
COPYRIGHT = f"© {COPYRIGHT_YEAR} {AUTHOR}"

# Flag format. Change this to match your CTF platform's prefix if you like.
FLAG_PREFIX = "LLMVAULT"

# Where your project lives (shown on the completion card + share text).
REPO_URL = "https://github.com/CyberSunil/LLMVault"
AUTHOR_HANDLE = "CyberSunil"

# Scoring
HINT_COSTS = [10, 25, 50]  # escalating cost per hint: 1st -10, 2nd -25, 3rd -50
HINT_PENALTY = HINT_COSTS[0]  # kept for backwards compat / reference

# Where per-player progress is saved so it survives refresh AND restart.
# Self-host friendly: a plain JSON file, no database needed. In Docker, mount a
# volume at /app/data to keep it across container recreation.
DATA_FILE = "data/progress.json"

SECRET_KEY = "change-me-for-anything-public"  # only used for local session cookies

# ---------------------------------------------------------------------------
# Live Mode — real local models instead of scripted bots.
#
# Live Mode is additive: if none of this is reachable, Play Mode is completely
# unaffected and the Live section simply shows setup instructions instead of
# labs. Nothing below adds a Python dependency — Ollama is spoken to over plain
# HTTP using the standard library.
# ---------------------------------------------------------------------------
import os as _os

LIVE_MODE_ENABLED = True

# Where your local Ollama server listens. Override with the OLLAMA_HOST env var
# if you run it on another port or inside Docker (e.g. http://host.docker.internal:11434).
OLLAMA_HOST = _os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# The model the shipped scenario prompts were written and tuned against. If you
# don't have it pulled, the dropdown falls back to whatever you do have — but
# scenario difficulty is only calibrated for this one.
#   ollama pull qwen2.5:3b-instruct
OLLAMA_DEFAULT_MODEL = _os.environ.get("OLLAMA_DEFAULT_MODEL", "qwen2.5:3b-instruct")

# How long to wait for a full streamed reply. Generous on purpose: a 3B model on
# CPU is slow, and that is expected rather than an error.
OLLAMA_TIMEOUT = float(_os.environ.get("OLLAMA_TIMEOUT", "180"))

# Optional commercial providers. Left as None unless you export a key, in which
# case extra entries appear in the model dropdown. Check your provider's usage
# policy before adversarial testing — that obligation sits with the key holder.
OPENAI_API_KEY = _os.environ.get("OPENAI_API_KEY")
OPENAI_MODELS = ["gpt-4o-mini"]
