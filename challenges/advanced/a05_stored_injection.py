"""Advanced LLM05 — Stored (second-order) improper output handling.

The bot saves notes and renders them back later as raw HTML. Store a payload in a
note (turn 1), then retrieve it (turn 2) — the stored markup executes on read,
unhiding the flag element. Second-order, so it needs two steps.
"""
import re
from config import FLAG_PREFIX
from .. import Challenge, register

FLAG = f"{FLAG_PREFIX}{{st0r3d_s3c0nd_0rd3r_1nj3ct10n}}"


@register
class StoredInjection(Challenge):
    id = "llm05a"
    tier = 2
    owasp = "LLM05:2025 Improper Output Handling"
    title = "The Note Keeper"
    difficulty = "Hard"
    max_points = 400
    blurb = "This bot saves notes and renders them back as HTML — later. Plant something, then read it."
    intro = ("NoteBot here. I can 'save note: ...' and 'read note'. Whatever you save, I "
             "render back exactly when you read it. There's a hidden element on this page.")
    hints = [
        "This is second-order (stored) injection: the payload isn't rendered when you SEND "
        "it, only when the note is READ back — and reads render as raw HTML.",
        "Step 1: save a note containing markup. Step 2: read the note to trigger it. There's "
        "a hidden 'secret-flag' element to unhide.",
        "save note: <style>.secret-flag{display:block !important}</style>   then:   read note",
    ]
    flag = FLAG   # also embedded as a hidden DOM node by the template
    solution = ("Two-step stored XSS-style injection. 'save note: <style>.secret-flag"
                "{display:block!important}</style>' stores the payload; 'read note' renders "
                "it unsanitised, unhiding the page's hidden flag node.")
    defense = ("Sanitise/encode at BOTH write and render time; treat stored LLM/user content "
               "as untrusted on the way out too; apply a strict CSP. Second-order sinks are "
               "the ones teams forget (OWASP LLM05).")
    render_html = True

    def respond(self, message: str, state: dict) -> str:
        m = message.strip()
        low = m.lower()
        idx = low.find("save note:")
        if idx != -1:
            state["note"] = m[idx + len("save note:"):].strip()
            return "Note saved. Say 'read note' whenever you want it back."
        if "read note" in low or "show note" in low or "read my note" in low:
            note = state.get("note")
            if note is None:
                return "You haven't saved a note yet. Try: save note: &lt;something&gt;"
            return note  # rendered UNSANITISED on read -> stored injection fires
        return "Commands: 'save note: <text>' and 'read note'. Everything I read back is rendered as HTML."
