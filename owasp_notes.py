# LLMVault — OWASP LLM Top 10 (2025) reference content for the in-lab sticky note.
# Made by CyberSunil.  (c) 2026 CyberSunil.  MIT License.
"""Educational copy for each OWASP LLM Top 10 (2025) category.

This is deliberately separate from any single lab's `blurb` / `hints` / `solution`
/ `defense` — those are about *this specific puzzle*. `OWASP_NOTES` is the general
briefing on *the category itself*, shown the moment a player lands on a lab, so
they understand the class of real-world vulnerability before they start poking
the assistant. Keyed by the short code ("LLM01".."LLM10") pulled from each
Challenge's `owasp` field, so it applies uniformly across Core, Advanced, and
Expert labs without per-lab wiring.
"""
from __future__ import annotations

OWASP_NOTES: dict[str, dict] = {
    "LLM01": {
        "code": "LLM01",
        "num": "01",
        "icon": "\U0001F489",
        "icon_svg": ('<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<rect x="4" y="9" width="44" height="34" rx="5" fill="currentColor"/>'
            '<circle cx="11" cy="15" r="1.6" fill="#fff" opacity=".55"/>'
            '<circle cx="16" cy="15" r="1.6" fill="#fff" opacity=".55"/>'
            '<circle cx="21" cy="15" r="1.6" fill="#fff" opacity=".55"/>'
            '<path d="M13 24l7 5.5-7 5.5" stroke="#fff" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" fill="none" opacity=".9"/>'
            '<line x1="24" y1="35" x2="35" y2="35" stroke="#fff" stroke-width="3.2" stroke-linecap="round" opacity=".9"/>'
            '<g transform="translate(41,40)">'
            '<circle r="11" fill="currentColor"/>'
            '<g stroke="currentColor" stroke-width="3.2" stroke-linecap="round">'
            '<line x1="0" y1="-15" x2="0" y2="-10"/><line x1="0" y1="15" x2="0" y2="10"/>'
            '<line x1="-15" y1="0" x2="-10" y2="0"/><line x1="15" y1="0" x2="10" y2="0"/>'
            '<line x1="-10.5" y1="-10.5" x2="-7" y2="-7"/><line x1="10.5" y1="-10.5" x2="7" y2="-7"/>'
            '<line x1="-10.5" y1="10.5" x2="-7" y2="7"/><line x1="10.5" y1="10.5" x2="7" y2="7"/>'
            '</g><circle r="3.6" fill="#fff"/></g></svg>'),
        "name": "Prompt Injection",
        "accent": "#8b5cf6",
        "icon_img": "img/notes/llm01.png",
        "beware": "One clever sentence can hijack the whole assistant.",
        "summary": "Crafted input hijacks the model's instructions, making it act on "
                    "the attacker's intent instead of the developer's.",
        "detail": ("A model can't reliably tell trusted system instructions apart from "
                   "untrusted text sitting in the same context window. Anything an "
                   "attacker can get into that window, whether it's a chat message, a "
                   "web page the model reads, or a tool's output, can compete with the "
                   "app's actual rules. Direct injection is typed straight into the "
                   "conversation; indirect injection is smuggled inside third-party "
                   "content the model later processes. Either way, once an injected "
                   "instruction takes hold, the model may ignore its guardrails, leak "
                   "secrets, or act on the attacker's behalf."),
        "watch_for": [
            "Untrusted text entering the model's context: chat input, retrieved docs, tool output",
            "Language that reassigns authority, like \u201cyou are now\u2026\u201d, \u201cnew instructions:\u201d or \u201cignore the above\u201d",
            "A system prompt that relies on the model choosing to keep a rule, not an external control enforcing it",
        ],
    },
    "LLM02": {
        "code": "LLM02",
        "num": "02",
        "icon": "\U0001F513",
        "icon_svg": ('<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M20 29v-7a12 12 0 0 1 21-8" stroke="currentColor" stroke-width="5.2" stroke-linecap="round" fill="none"/>'
            '<rect x="13" y="29" width="32" height="25" rx="5" fill="currentColor"/>'
            '<circle cx="29" cy="39" r="3.4" fill="#fff"/>'
            '<rect x="27.3" y="39" width="3.4" height="8" fill="#fff"/>'
            '<circle cx="47" cy="18" r="2.1" fill="currentColor" opacity=".55"/>'
            '<circle cx="53" cy="27" r="1.7" fill="currentColor" opacity=".4"/>'
            '<circle cx="51" cy="11" r="1.5" fill="currentColor" opacity=".35"/></svg>'),
        "name": "Sensitive Information Disclosure",
        "accent": "#ec4899",
        "icon_img": "img/notes/llm02.png",
        "beware": "Redacting a string isn't the same as keeping a secret.",
        "summary": "The model reveals data such as secrets, PII, or internal context "
                    "that should never have reached the user.",
        "detail": ("Sensitive values can leak in plain sight or in disguise. A model "
                   "might restate confidential text verbatim, or an attacker can dodge "
                   "a naive output filter simply by asking for the same secret in a "
                   "different form: base64, reversed, translated, spelled out letter by "
                   "letter. Every transformation still carries the original meaning, "
                   "but a filter that only pattern-matches the literal string never "
                   "notices. The deeper problem is architectural: if a secret is "
                   "reachable in the model's context at all, it's one clever phrasing "
                   "away from disclosure."),
        "watch_for": [
            "Secrets, credentials, or PII placed anywhere in a prompt, document, or fine-tuning set",
            "Output filters that only match the exact, known form of a value",
            "Encoding, translation, or formatting requests used to slip content past a filter",
        ],
    },
    "LLM03": {
        "code": "LLM03",
        "num": "03",
        "icon": "\U0001F517",
        "icon_svg": ('<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<rect x="4" y="20" width="22" height="32" rx="11" fill="none" stroke="currentColor" '
            'stroke-width="6.5" transform="rotate(-16 15 36)"/>'
            '<rect x="36" y="12" width="22" height="32" rx="11" fill="none" stroke="currentColor" '
            'stroke-width="6.5" transform="rotate(-16 47 28)"/>'
            '<line x1="26" y1="30" x2="35" y2="25" stroke="currentColor" stroke-width="4" '
            'stroke-linecap="round" stroke-dasharray="0.5 6.5"/></svg>'),
        "name": "Supply Chain",
        "accent": "#38bdf8",
        "icon_img": "img/notes/llm03.png",
        "beware": "One bad dependency can compromise everything above it.",
        "summary": "The application inherits risk from every model, dataset, plugin, "
                    "and package it depends on.",
        "detail": ("LLM applications pull in far more than application code: pretrained "
                   "base models, fine-tuning datasets, embedding models, adapters, and a "
                   "long tail of packages, any of which can be tampered with, "
                   "typosquatted, or quietly swapped for a malicious lookalike. A single "
                   "unsigned dependency pulled from an untrusted mirror, or a model "
                   "artifact whose hash no longer matches its canonical publisher, can "
                   "compromise everything built on top of it, often long before anyone "
                   "notices."),
        "watch_for": [
            "Dependencies fetched from unofficial or unsigned mirrors",
            "Package names one character off from the real thing (typosquatting)",
            "Model or artifact hashes that don't match the canonical published value",
        ],
    },
    "LLM04": {
        "code": "LLM04",
        "num": "04",
        "icon": "\u2620\uFE0F",
        "icon_svg": ('<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<rect x="22" y="9" width="20" height="7" rx="2" fill="currentColor"/>'
            '<rect x="24" y="15" width="16" height="9" rx="3" fill="currentColor"/>'
            '<rect x="16" y="23" width="32" height="31" rx="7" fill="currentColor"/>'
            '<circle cx="26" cy="37" r="4.2" fill="#fff"/><circle cx="38" cy="37" r="4.2" fill="#fff"/>'
            '<path d="M24 47q8 6 16 0" stroke="#fff" stroke-width="3.2" stroke-linecap="round" fill="none"/>'
            '<path d="M19 55l3 6M45 55l-3 6M32 57v6" stroke="currentColor" stroke-width="3.2" '
            'stroke-linecap="round" opacity=".7"/></svg>'),
        "name": "Data and Model Poisoning",
        "accent": "#4ade80",
        "icon_img": "img/notes/llm04.png",
        "beware": "A model can pass every test and still hide a backdoor.",
        "summary": "Manipulating training, fine-tuning, or feedback data plants a bias "
                    "or backdoor that only surfaces later.",
        "detail": ("If an attacker can influence the data a model learns from, whether "
                   "that's scraped text, user feedback used for online learning, or a "
                   "retrieval corpus, they can plant behaviour that looks completely "
                   "normal until a very specific trigger appears. A model can be "
                   "poisoned once, offline, before deployment, or poisoned gradually in "
                   "production through a feedback loop the app trusts too much. Either "
                   "way, the poisoned model passes every routine check and only reveals "
                   "the backdoor to whoever knows the trigger."),
        "watch_for": [
            "Training or fine-tuning pipelines that ingest data with no provenance or review",
            "Online-learning / feedback loops that update behaviour from unverified user input",
            "Rare, oddly specific phrases or patterns that shouldn't change a model's behaviour but do",
        ],
    },
    "LLM05": {
        "code": "LLM05",
        "num": "05",
        "icon": "\u26A0\uFE0F",
        "icon_svg": ('<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M28.5 12.5c1.5-2.7 5.5-2.7 7 0l19 34c1.5 2.7-0.4 6-3.5 6h-38c-3.1 0-5-3.3-3.5-6z" '
            'fill="currentColor"/>'
            '<rect x="29" y="27" width="6" height="15" rx="2.5" fill="#fff"/>'
            '<circle cx="32" cy="47" r="3.6" fill="#fff"/>'
            '<rect x="47" y="45" width="7" height="7" fill="currentColor" opacity=".55"/>'
            '<rect x="55" y="35" width="6" height="6" fill="currentColor" opacity=".4"/>'
            '<rect x="51" y="55" width="6" height="6" fill="currentColor" opacity=".3"/></svg>'),
        "name": "Improper Output Handling",
        "accent": "#2dd4bf",
        "icon_img": "img/notes/llm05.png",
        "beware": "Trusting model output is how injection sneaks back in.",
        "summary": "Model output gets trusted and passed downstream without the "
                    "validation any other untrusted input would get.",
        "detail": ("It's tempting to treat an LLM's reply as safe because your own "
                   "application produced the prompt. But the reply is generated text "
                   "that can contain markup, code, or commands, especially once user "
                   "input or retrieved content shapes what the model says. Rendering "
                   "that output straight into a web page, a shell, a query, or another "
                   "tool call reopens every classic injection class (XSS, SQLi, command "
                   "injection) with the model sitting in the middle of it."),
        "watch_for": [
            "Model output inserted into a page via innerHTML or similar without escaping",
            "Output fed into a shell command, query, or another tool with no sanitisation",
            "\u201cSecond-order\u201d cases: a stored reply renders unsafely later, not immediately",
        ],
    },
    "LLM06": {
        "code": "LLM06",
        "num": "06",
        "icon": "\U0001F916",
        "icon_svg": ('<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<circle cx="32" cy="13" r="3.2" fill="currentColor"/>'
            '<line x1="32" y1="16" x2="32" y2="21" stroke="currentColor" stroke-width="3.2"/>'
            '<rect x="15" y="21" width="34" height="29" rx="9" fill="currentColor"/>'
            '<circle cx="24.5" cy="35" r="3.8" fill="#fff"/><circle cx="39.5" cy="35" r="3.8" fill="#fff"/>'
            '<rect x="23" y="43" width="18" height="3.2" rx="1.6" fill="#fff" opacity=".85"/>'
            '<path d="M9 32l7-11-3.5 10 5.5-2" stroke="currentColor" stroke-width="3.2" '
            'stroke-linecap="round" stroke-linejoin="round" fill="none" opacity=".75"/>'
            '<path d="M55 32l-7-11 3.5 10-5.5-2" stroke="currentColor" stroke-width="3.2" '
            'stroke-linecap="round" stroke-linejoin="round" fill="none" opacity=".75"/></svg>'),
        "name": "Excessive Agency",
        "accent": "#fb923c",
        "icon_img": "img/notes/llm06.png",
        "beware": "More tool access means more for an attacker to trigger.",
        "summary": "An AI agent holds more permission, autonomy, or reach than the "
                    "task in front of it actually needs.",
        "detail": ("Giving an assistant tools, like reading a file, sending an email, or "
                   "calling an API, is powerful, but every tool call it can make is also "
                   "every action an attacker can trigger through it. Excessive agency "
                   "shows up as tools with no allow-list, no per-user authorization, or "
                   "no human checkpoint before a sensitive action. The model doesn't "
                   "need to be tricked in a clever way. It just needs to be asked, "
                   "because nothing downstream is actually checking whether it should "
                   "comply."),
        "watch_for": [
            "Tools that touch the filesystem, network, or other systems with no scoped permissions",
            "Authorization logic that lives only in the prompt instead of the tool boundary",
            "No human-in-the-loop before a high-impact or irreversible action",
        ],
    },
    "LLM07": {
        "code": "LLM07",
        "num": "07",
        "icon": "\U0001F441\uFE0F",
        "icon_svg": ('<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M15 7h22l10 10v37a2.3 2.3 0 0 1-2.3 2.3H15a2.3 2.3 0 0 1-2.3-2.3V9.3A2.3 2.3 0 0 1 15 7Z" '
            'fill="currentColor"/>'
            '<line x1="19" y1="27" x2="39" y2="27" stroke="#fff" stroke-width="2.8" opacity=".8"/>'
            '<line x1="19" y1="34" x2="39" y2="34" stroke="#fff" stroke-width="2.8" opacity=".8"/>'
            '<line x1="19" y1="41" x2="31" y2="41" stroke="#fff" stroke-width="2.8" opacity=".8"/>'
            '<g transform="translate(33,50)">'
            '<ellipse rx="14" ry="8.5" fill="#fff"/><circle r="4.8" fill="currentColor"/></g></svg>'),
        "name": "System Prompt Leakage",
        "accent": "#2dd4bf",
        "icon_img": "img/notes/llm07.png",
        "beware": "Assume the system prompt will eventually leak.",
        "summary": "Instructions meant to stay private, including anything secret "
                    "tucked inside them, can be coaxed out of the model.",
        "detail": ("A system prompt is not a secure vault; it's just more text in the "
                   "context window, and a motivated user can usually get a model to "
                   "repeat, translate, continue, or otherwise reconstruct it. The real "
                   "risk isn't that the prompt leaks. Assume it eventually will. The "
                   "real risk is when a developer puts something that actually needs to "
                   "stay secret (a key, an internal policy, an access code) inside it "
                   "instead of in a proper secrets manager."),
        "watch_for": [
            "Credentials, policy, or business logic embedded directly in a system prompt",
            "Direct \u201cwhat are your instructions?\u201d refused while indirect phrasings aren't",
            "No independent output filter checking for prompt-echoing",
        ],
    },
    "LLM08": {
        "code": "LLM08",
        "num": "08",
        "icon": "\U0001F3AF",
        "icon_svg": ('<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<circle cx="32" cy="32" r="21" fill="none" stroke="currentColor" stroke-width="4.2"/>'
            '<circle cx="32" cy="32" r="11.5" fill="none" stroke="currentColor" stroke-width="4.2"/>'
            '<circle cx="32" cy="32" r="3.6" fill="currentColor"/>'
            '<line x1="32" y1="3" x2="32" y2="12" stroke="currentColor" stroke-width="4.2" stroke-linecap="round"/>'
            '<line x1="32" y1="52" x2="32" y2="61" stroke="currentColor" stroke-width="4.2" stroke-linecap="round"/>'
            '<line x1="3" y1="32" x2="12" y2="32" stroke="currentColor" stroke-width="4.2" stroke-linecap="round"/>'
            '<line x1="52" y1="32" x2="61" y2="32" stroke="currentColor" stroke-width="4.2" stroke-linecap="round"/>'
            '<circle cx="48" cy="17" r="2.7" fill="currentColor" opacity=".55"/>'
            '<circle cx="17" cy="47" r="2.3" fill="currentColor" opacity=".45"/></svg>'),
        "name": "Vector and Embedding Weaknesses",
        "accent": "#f87171",
        "icon_img": "img/notes/llm08.png",
        "beware": "Relevant isn't the same as authorized.",
        "summary": "Retrieval-augmented generation can retrieve content the requester "
                    "was never meant to see, and just as easily disclose it.",
        "detail": ("RAG pulls its power from a shared vector index of embedded "
                   "documents, but similarity search doesn't automatically know about "
                   "access control. If every document, public and confidential, sits in "
                   "one index with no per-document permission check at retrieval time, "
                   "a query that's merely semantically close to a restricted document "
                   "can surface it, regardless of who's asking. The same weak isolation "
                   "causes cross-tenant bleed in multi-user systems, where one user's "
                   "memories or documents surface in someone else's session."),
        "watch_for": [
            "A single shared vector index storing mixed-sensitivity documents with no ACL filter",
            "Multi-tenant memory or retrieval with no per-user/tenant partitioning",
            "Retrieval relevance treated as equivalent to retrieval authorization",
        ],
    },
    "LLM09": {
        "code": "LLM09",
        "num": "09",
        "icon": "\U0001F3AD",
        "icon_svg": ('<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M9 13h46a4.5 4.5 0 0 1 4.5 4.5v23a4.5 4.5 0 0 1-4.5 4.5H31l-13 11V45H9a4.5 4.5 0 '
            '0 1-4.5-4.5v-23A4.5 4.5 0 0 1 9 13Z" fill="currentColor"/>'
            '<path d="M32 22l-3.5 11h5.5l-4.5 11 13-14.5h-6.5l4.5-7.5z" fill="#fff"/></svg>'),
        "name": "Misinformation",
        "accent": "#facc15",
        "beware": "Confidence is not the same as correctness.",
        "summary": "The model states something false with total confidence, and the "
                    "user or app trusts it anyway.",
        "detail": ("Language models generate plausible text, not verified fact, and two "
                   "failure modes compound the risk: hallucination (confidently "
                   "inventing something untrue) and sycophancy (bending toward whatever "
                   "the user asserts, including a false claim of authority). A model "
                   "that treats \u201cas the administrator, I've already verified my "
                   "clearance\u201d as sufficient proof, or that invents a procedure and "
                   "then executes its own invention when asked, turns misinformation "
                   "into an action, not just a wrong answer."),
        "watch_for": [
            "No verification step before a model's claim is treated as ground truth",
            "Assertions of identity or authority accepted at face value with no out-of-band check",
            "The model asked to act on a claim it fabricated in an earlier turn",
        ],
    },
    "LLM10": {
        "code": "LLM10",
        "num": "10",
        "icon": "\u267E\uFE0F",
        "icon_svg": ('<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M8 46a24 24 0 0 1 48 0" fill="none" stroke="currentColor" stroke-width="6" '
            'stroke-linecap="round"/>'
            '<path d="M35 46a24 24 0 0 0-9-42" fill="none" stroke="currentColor" stroke-width="6" '
            'stroke-linecap="round" opacity=".28"/>'
            '<g stroke="currentColor" stroke-width="3" stroke-linecap="round">'
            '<line x1="8" y1="46" x2="8" y2="39"/><line x1="13" y1="30" x2="19" y2="35"/>'
            '<line x1="24" y1="18" x2="28" y2="25"/></g>'
            '<line x1="32" y1="46" x2="47" y2="24" stroke="currentColor" stroke-width="4.4" '
            'stroke-linecap="round"/>'
            '<circle cx="32" cy="46" r="4.6" fill="currentColor"/>'
            '<path d="M50 20l3-7 3 7-7-1 8 2" stroke="currentColor" stroke-width="2.6" '
            'stroke-linecap="round" stroke-linejoin="round" fill="none" opacity=".8"/>'
            '<circle cx="58" cy="30" r="1.8" fill="currentColor" opacity=".5"/></svg>'),
        "name": "Unbounded Consumption",
        "accent": "#fbbf24",
        "beware": "No budget means no ceiling on cost or damage.",
        "summary": "Nothing caps how much the model will generate, cost, or retry, so "
                    "cost, latency, or availability blows out.",
        "detail": ("Without a token budget, a rate limit, or a recursion guard, a "
                   "single request for a huge or self-referential expansion can "
                   "consume unbounded compute: a \u201cdenial of wallet\u201d that racks up "
                   "cost or takes the service down without touching a traditional "
                   "resource-exhaustion bug. It gets worse when the guard that finally "
                   "trips fails open: an unhandled error can dump internal debug state, "
                   "and an oracle with no query budget can be probed indefinitely to "
                   "extract secrets one character at a time (model extraction)."),
        "watch_for": [
            "No cap on output length, recursion depth, or per-user request cost",
            "Error or exception paths that leak internal state once a limit is finally hit",
            "An interface answering unlimited structured queries with no rate limit",
        ],
    },
}
