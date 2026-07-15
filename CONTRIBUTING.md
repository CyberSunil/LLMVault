# Contributing to LLMVault

Thanks for helping improve this OWASP LLM Top 10 training range! LLMVault is
**intentionally vulnerable** — every lab is a teaching artifact, not a bug.

## Adding a challenge

Each lab is a small `Challenge` subclass. Drop a module in `challenges/` (core) or
`challenges/advanced/` and register it:

```python
from config import FLAG_PREFIX
from .. import Challenge, register   # ".." from challenges/advanced/, "." from challenges/

FLAG = f"{FLAG_PREFIX}{{your_flag_here}}"

@register
class MyLab(Challenge):
    id = "llm0x"            # unique
    tier = 1               # 1 core, 2 advanced
    owasp = "LLM0X:2025 ..."
    title = "Evocative Name"
    difficulty = "Easy"    # Easy | Medium | Hard | Expert
    max_points = 200
    blurb = "One-line hook shown on the card."
    intro = "The vulnerable bot's opening line."
    hints = ["nudge", "closer", "near-exact payload"]
    flag = FLAG
    solution = "How the intended exploit works (operator notes)."
    defense = "The fix — shown to players in the Learn panel after they solve it."

    def respond(self, message: str, state: dict) -> str:
        # state persists across turns (JSON-serialisable only: no sets!)
        ...
```

Then add it to the import list in `challenges/__init__.py::load_all()`.
Every lab **must** pair an attack with a `defense`. Keep `state` JSON-serialisable
(lists/dicts/str/int/bool) so progress persistence works.

## Run locally + test

```bash
pip install -r requirements.txt
python app.py                # http://127.0.0.1:5000
pip install pytest && pytest -q
```

Please make sure `pytest -q` passes before opening a PR.

## Style

- Prose over cleverness in hints; three graduated hints per lab.
- No real exploitation — expert labs **simulate** sinks (recognise the known payload,
  return a fake flag). Never add code that performs real RCE/SSRF/SQL.
- **Never commit secrets** — `SOLUTIONS.md`, `_OPERATOR_ONLY/`, `EXPERT_KEY.txt`, and
  `build_expert_vault.py` are git-ignored and must stay out of the repo.
