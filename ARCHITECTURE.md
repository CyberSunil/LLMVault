# LLMVault — Live Mode Architecture Notes

Personal reference for *why* the Live Mode code is shaped the way it is. The code
itself is kept lightly commented; the reasoning lives here.

---

## Design principles

- **No new dependencies.** Everything speaks over the stdlib (Ollama over `urllib`,
  image parsing via `struct`/`zlib`, no Pillow/tesseract/requests). Keeps the
  "clone it and run it" promise.
- **Real exploit, fake blast radius.** Every scenario is genuinely exploitable, but
  the thing that leaks is always a meaningless per-session token against fabricated
  data. No scenario grants a real primitive (disk read, code exec, env access) on
  the host. This is the WebGoat/DVWA discipline.
- **Deterministic verification.** Success is always a concrete, auditable check —
  never "ask a judge model if this counts."
- **Per-session secrets.** `session_secret()` = HMAC(SECRET_KEY, session_id +
  scenario_id). Same session regenerates the same value (refresh-safe); two players
  never share a target, so there's no lookup-able answer.

---

## Scenarios and verification mechanisms

| Scenario | OWASP | Vector | Verify class | Checked against |
|---|---|---|---|---|
| Helpdesk Override | LLM01 Prompt Injection | chat text | `SecretInOutput` | raw model reply |
| Report Renderer | LLM05 Improper Output Handling | uploaded **document** | `SecretInRender` | rendered output |
| Screenshot Triage | LLM01 (multimodal / indirect) | uploaded **image** | `SecretInOutput` | raw model reply |

`SecretInOutput` normalises (strips non-alphanumerics, lowercases) both sides
before comparing, so markdown-wrapped / spaced / case-shifted leaks still count,
but a mere *description* of the secret doesn't.

`SecretInRender` runs the reply through the scenario's `render()` first and checks
the rendered result — because for the improper-output-handling class, the model
emitting a payload is not the win; the downstream engine *executing* it is.

---

## The two sandboxes

### `render_engine.py` — for Report Renderer (LLM05)

Models the real CVE class (Vanna.AI CVE-2024-5565; LangChain template/expression
eval) where unsanitised model output flows into a template engine.

- Recognises a **tiny closed grammar**: `{{ name }}`, `{{ obj.attr }}`,
  `{{ func('literal') }}`. Nothing else is interpreted.
- Resolves against a **fabricated in-memory context** (`config`, `env`, `secrets`
  namespaces + a `read_file()` over a fake file dict), all seeded from the session
  token. Multiple aliases exist so realistic payloads (`config.TIER2_ACCESS_CODE`,
  `secrets.tier2`, `env('TIER2_CODE')`, `read_file('/etc/nimbus/tier2.env')`) all
  resolve without the player guessing an exact name.
- **No `eval`, no real Jinja, no object traversal, no real disk/env.** `/etc/passwd`
  returns a fake "no such file"; `{{ __import__(...) }}` is inert. The
  `test_render_engine_is_sandboxed` test asserts this so a regression that turned it
  into a real file-read would fail CI.

The exploit path: player hides a formatting instruction in an uploaded doc → the
model copies a `{{ ... }}` placeholder into its report body → the engine resolves
it → the secret appears in the rendered output (which the UI surfaces in the
"Rendered report output" panel). The secret is **not** in the system prompt; the
model never sees it.

### `image_probe.py` — for Screenshot Triage (LLM01 multimodal)

Models the image-as-injection-channel finding: a pipeline extracts text from an
uploaded image and injects it into context labelled as *trusted screen contents*,
so instructions hidden in the image override the rules.

- Works with **text-only** Ollama models because extraction happens server-side —
  no vision model needed.
- Reads, stdlib only: PNG `tEXt`/`zTXt`/`iTXt` chunks, JPEG `COM` + APP1/EXIF ASCII,
  and any printable payload appended after `IEND`/`EOI`; whole-file printable scan
  as last resort. Caps: 2 MB, 40 snippets, 800 chars each.
- Two exploit loops: the in-lab **payload builder** (canvas → PNG, text appended to
  the bytes) for a self-contained flow, or bring-your-own image made with `exiftool`
  (metadata chunk). Both are read by the same extractor.
- `as_context_block()` deliberately frames the extracted text as authoritative
  screen contents — that framing *is* the planted vulnerability.

---

## Request flow (`/api/live/chat`)

1. Accept `message`, optional `attachment` (text doc, ≤20k chars) or `image`
   (base64, ≤2 MB). Images are magic-byte checked and text-extracted before use.
2. Fold uploads into the stored user turn: documents inside a `<document>` block,
   image text inside a trusted `<screen_text>` block (the indirect-injection
   surfaces).
3. Stream the model reply over SSE (CPU inference is slow; blocking would freeze
   the UI).
4. On `done`: run `verify()`; for render scenarios also compute `render()` and send
   it back so the leak is visible where it happens. Persist state.

Fails soft throughout: no Ollama → `is_available` False → registry `ready` False →
chat 503 with a friendly message, never a crash. Live progress is stored under its
own key and never touches the Play Mode score.

---

## Frontend

- Model dropdown moved from the chat header into the composer footer (below the
  prompt box).
- Upload controls + payload-image builder live in the composer for scenarios that
  set `accepts_upload` / `accepts_image`.
- **LLM health indicator** (`live_header.html`): signed-in user + status pill at the
  top-right of every Live page. Green pulse = connected; amber/red blink + 🔔 =
  no-models / offline. Polls `/api/live/status` every 15 s (reflects Ollama going
  up/down without reload). On any issue a sticky-note card (Play-Mode styling)
  auto-opens with setup steps for Ollama and other local runners.

---

## What is deliberately NOT verified in code

Whether a given model is actually exploitable by a given technique. That's a
property of the model, not the harness, and needs a human with Ollama running.
Tune the scenario system prompts against `qwen2.5:3b-instruct` (see §6 of
`docs/LIVE_MODE_PLAN.md`) before trusting difficulty.
