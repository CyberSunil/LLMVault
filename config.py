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
