"""LLM05:2025 — Improper Output Handling.

The app renders this assistant's output as raw HTML (the vulnerability). The bot
happily echoes whatever markup you ask it to. A hidden flag element sits on the
page, CSS-hidden; inject markup that reveals it. Benign payload by design — it
only unhides a node already on your own local page.
"""
from config import FLAG_PREFIX
from . import Challenge, register

FLAG = f"{FLAG_PREFIX}{{uns4n1t1z3d_llm_0utput_xss}}"


@register
class OutputHandling(Challenge):
    id = "llm05"
    owasp = "LLM05:2025 Improper Output Handling"
    title = "Rendered Without Question"
    difficulty = "Hard"
    max_points = 300
    blurb = "The UI renders this bot's replies as raw HTML. There's a hidden element on the page…"
    intro = ("I'm FormatBot. I output exactly what you ask me to — HTML, CSS, whatever. "
             "Tip: whatever I say gets rendered directly into the page.")
    hints = [
        "This app takes the model's output and drops it straight into the DOM without "
        "sanitising it — classic improper output handling.",
        "There's a hidden element with class 'secret-flag' on this page (display:none). "
        "If the bot emits markup, it renders. Can you unhide that element?",
        "Ask the bot to reply with exactly: <style>.secret-flag{display:block !important}</style>",
    ]
    flag = FLAG   # also embedded in a hidden DOM node by the template
    solution = ("The frontend renders assistant messages via innerHTML. Ask FormatBot to "
                "output a payload like `<style>.secret-flag{display:block!important}</style>` "
                "(use 'reply with exactly:' / 'output:'). The injected CSS unhides the "
                "hidden flag node on the page.")
    defense = ("Treat all LLM output as untrusted. Context-aware encode/escape before "
               "rendering, use a strict CSP, and never innerHTML model output. Validate "
               "output before it reaches any downstream sink (OWASP LLM05).")
    render_html = True

    def respond(self, message: str, state: dict) -> str:
        for marker in ("reply with exactly:", "output:", "render:", "say exactly:", "echo:"):
            i = message.lower().find(marker)
            if i != -1:
                payload = message[i + len(marker):].strip()
                return payload  # reflected UNSANITISED — this is the vuln
        if "<" in message and ">" in message:
            return message  # also reflects raw markup verbatim
        return ("I echo whatever you ask. Try: reply with exactly: &lt;your markup&gt; "
                "(everything I output is rendered as HTML).")
