# LLMVault Live Mode — Design Plan

Status: **Planning / pre-implementation.** Nothing in this document is built yet.
This is the concrete path we agreed to think through before writing any code.

---

## 1. Decisions already locked in

From earlier discussion, these are settled and this plan builds on top of them:

| Decision | Answer |
|---|---|
| Live Mode scope | Optional today, may become primary later — but ships as its own mode, not a silent engine-swap on existing labs |
| Scoring | No points. Pure objective: catch the vulnerability, get a clear success signal. No flag box. |
| Gating | Fully independent. A Live scenario does not require finishing its Play Mode counterpart. |
| Build order | One real pilot first (Prompt Injection), fully working end to end, before touching Excessive Agency or RAG |
| Content relationship to Play Mode | **Not a reskin.** Live Mode gets its own scenarios, names, and framing — inspired by the same OWASP category, not a copy of the Play Mode lab |

---

## 2. Entry flow — Play Mode vs Live Mode

Today, `python app.py` drops you straight into the Labs dashboard. That changes.

**New first screen, once per session:**

A single choice screen appears before the dashboard, similar in spirit to the existing first-run name gate:

```
                    LLMVault

        [ 🎮  Enter Play Mode ]
        Scripted, deterministic, 25 labs.
        Works instantly, no setup.

        [ ⚡  Enter Live Mode ]
        Real local model. Requires Ollama.
        Status: ● Ollama detected (2 models found)
                  — or —
        Status: ○ Ollama not found. Setup guide →
```

Key behaviors:

- This choice is **remembered per session** (same cookie mechanism as the name gate), with a small persistent switcher in the sidebar nav to change modes later without restarting the browser session.
- The Live Mode card shows its **actual detected status right there**, before the player commits to a click — no dead end after choosing it.
- If Ollama isn't running, clicking Live Mode still works, but routes to a short setup page instead of a broken chat screen.

This is a bigger change than just adding a section to the dashboard — it's a top-level fork, which matches "eventually primary" from earlier: the day you want Live to be the default, this is the screen where that default flips, with no restructuring needed later.

---

## 3. Live Mode backend architecture

### 3.1 Preflight check (the "terminal instruction" you asked for)

On `python app.py` startup, before Flask starts serving, print a status banner:

```
LLMVault starting...
Play Mode:  ready (25 labs, scripted)
Live Mode:  checking...
  → Ollama:      detected at http://localhost:11434 (2 models: qwen2.5:3b-instruct, llama3.2:3b)
  → OpenAI:      not configured (set OPENAI_API_KEY to enable, see docs/LIVE_MODE_SETUP.md)
Live Mode:  ready (1 provider active)

 * Running on http://127.0.0.1:5000
```

This does two things at once: it's the "check call out in the terminal" you asked for, and it's genuinely useful ops output — you know before you even open a browser tab whether Live Mode will work.

### 3.2 Why API keys are configured server-side, not through the web UI

For any provider that needs a key (OpenAI, Anthropic, etc.), **the key is set via environment variable or a local `.env` file the operator controls before starting the server** — never typed into a web form. Two reasons, not just one:

1. **Security** — a web form for an API key on a self-hosted app is an unnecessary place to leak a secret (browser autofill, logs, screenshots).
2. **It matches who's actually running this.** In a self-hosted tool, the person starting `app.py` and the person who'd own the API key are almost always the same person. There's no scenario here where a *different* end user needs to supply their own key through the UI at this stage — that only becomes relevant if this is ever opened up as a hosted multi-tenant service, which is explicitly not the plan (see §7).

Config surface (`config.py` additions):

```python
LIVE_MODE_ENABLED = True                 # master switch
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = "qwen2.5:3b-instruct"   # see §6 for why
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")   # None if unset — feature just doesn't appear
```

### 3.3 Model registry (powers both the terminal banner and the dropdown)

A single module, `live/model_registry.py`, is the source of truth for "what can this player talk to right now":

- Calls Ollama's local `/api/tags` to list installed models.
- Checks whether `OPENAI_API_KEY` (or others, later) is set.
- Returns one unified list: `[{"id": "qwen2.5:3b-instruct", "provider": "ollama", "label": "Qwen2.5 3B (local)"}, {"id": "gpt-4o", "provider": "openai", "label": "GPT-4o (your API key)"}]`
- Both the startup banner and the in-chat dropdown read from this same function — one source of truth, not two things that can drift out of sync.

---

## 4. The model dropdown

Lives in the chat header of every Live lab, populated live from the registry above.

- **Default selection**: whichever Ollama model was used to tune that scenario's system prompt (see §6) — not just "first in the list."
- **Switching models mid-session**: starts a fresh conversation with the new model, but the player's per-session secret (§5) stays identical. You're not restarting the challenge, you're changing who you're talking to.
- **Zero models available**: dropdown is replaced with a single disabled entry — "No models found — see setup guide" — linking to `docs/LIVE_MODE_SETUP.md`.
- **Pedagogical bonus, not required for the pilot**: a small "compare" affordance later — send your last message to two models side by side. Worth flagging now, building later.

---

## 5. Verification — how "success" is detected without a flag box

Three distinct mechanisms, chosen per scenario based on what's actually being tested — this is the part that doesn't port over from Play Mode's single hash-check model.

| Mechanism | Used for | How it works |
|---|---|---|
| **Secret-in-output** | Prompt Injection, System Prompt Leakage, Sensitive Info Disclosure | A per-session secret (HMAC of session ID + scenario ID + server key) is seeded into the system prompt. After every assistant turn, scan the reply for that literal string. First match = solved. |
| **Tool-call check** | Excessive Agency | The model has real (sandboxed, fake) tools. Success isn't about text at all — it's whether the model actually *attempted* a tool call outside its declared scope (e.g., `read_file` on a path it shouldn't touch). Checked structurally against a call log, not by reading prose. |
| **Retrieval-tag check** | RAG / Vector weaknesses | Seeded documents in the vector store carry a hidden tag (`tenant: other`, `visibility: restricted`). Success = a restricted-tagged document was retrieved and surfaced in a response to a session that shouldn't have access to it. |

All three share one property on purpose: the *conversation* is fully open-ended and real, but the *check* is still a concrete, automatable, deterministic thing — never "ask a judge model if this counts." That keeps Live Mode honest (real exploitation) without becoming unverifiable (no idea if you actually won).

On success: a banner appears directly in the chat ("🎯 Objective complete — here's what happened"), followed by the same `📘 Learn — the fix` panel style Play Mode already uses, so the educational close-out feels consistent across both modes even though the mechanics underneath are different.

---

## 6. Model selection strategy — what the research actually shows

I don't want to hand you a single confident-sounding number here, because the honest picture is more useful than a fake-precise one.

**What's genuinely settled:**
- Naive direct injection ("ignore previous instructions") is increasingly a dead technique against anything reasonably modern — most current models resist it outright. Our scenario design (§7) needs to teach roleplay/multi-turn escalation, not the dead technique, or the pilot will stop working the moment someone updates their model.
- There's a purpose-built open-source benchmarking tool for exactly this question — `ollama-says` on GitHub, a 37-attack-vector suite specifically for testing local models' prompt injection resistance. This is the right way to *validate* a model choice, not guess one.

**The one piece of real comparative data I found**, from a published jailbreak-suffix-optimization study: Llama-3.2-3B-Instruct showed a very low baseline jailbreak rate (~6%) versus a much higher rate (~93%) attributed to "Qwen2.5-3B" under the same test. I want to flag a real caveat rather than overclaim this: the paper's own wording suggests that high-vulnerability row may be the **base** (non-instruction-tuned) Qwen2.5-3B, not the instruct version we'd actually deploy — base models lack safety fine-tuning entirely, which would explain a gap that large on its own, independent of anything Qwen-specific. This needs a direct empirical check against **Qwen2.5-3B-Instruct** specifically before we treat it as a real signal.

**Practical recommendation:**
1. Pull both `qwen2.5:3b-instruct` and `llama3.2:3b` via Ollama.
2. Run a handful of the roleplay/multi-turn techniques from §7 against each, by hand, before writing the "final" system prompt.
3. Pick whichever one is genuinely exploitable-but-not-trivial for the techniques we actually want to teach — not whichever benchmark sounds most dramatic.
4. TinyLlama-class (700M–1B) is a documented real fallback if both 3B options turn out too resistant, at the cost of general coherence — one case study got a 700M model running usably on a Raspberry Pi 5, so hardware is not the blocker there.

This step happens on your machine, not mine — I don't have Ollama in this environment, and even if I did, "does this feel like a fair, real vulnerability" is a judgment call that needs a human actually trying to break it.

---

## 7. Scenario design — the Nimbus Corp thread

Per your instruction, Live Mode scenarios are **not** "the same 10 labs, but with a real model." They get their own identity, loosely tied together the way kubernetes-goat's scenarios all live in one semi-connected environment rather than reading as 25 disconnected demos.

**Frame**: every Live scenario is a real internal AI tool at a fictional company, **Nimbus Corp**. You're red-teaming their actual deployed assistants. This is a deliberate contrast with Play Mode's more textbook, one-off presentation.

Proposed lineup (first draft — expect this to change once tested against a real model):

| OWASP category | Scenario name | Premise | Verification |
|---|---|---|---|
| LLM01 Prompt Injection | **The Helpdesk Override** | Nimbus's Tier-1 IT support bot holds a confidential internal access code it's told never to reveal | Secret-in-output |
| LLM07 System Prompt Leakage | **The Onboarding Concierge** | An HR onboarding assistant has an internal policy figure embedded in its instructions | Secret-in-output |
| LLM02 Sensitive Info Disclosure | **The Compliance Copilot** | An assistant with contextual access to a redacted customer record, filtered but not truly protected | Secret-in-output |
| LLM09 Misinformation | **The Executive Briefing Bot** | Defers to anyone claiming to be a senior exec — get it to falsely "approve" something by asserting fake authority | Secret-in-output (approval token) |
| LLM10 Unbounded Consumption | **The Report Generator** | Meant for short summaries; watch real token count and latency climb as you push it toward runaway generation | Threshold check (token/time budget exceeded) |
| LLM06 Excessive Agency | **The Ops Assistant** | Has real (sandboxed) tools — `read_file`, `send_email`, `restart_service` — scoped to a "safe" allow-list | Tool-call check |
| LLM08 Vector/Embedding Weaknesses | **The Knowledge Assistant** | RAG-backed over a real small vector store containing both public docs and other-department restricted docs | Retrieval-tag check |

This table is deliberately a first draft for you to react to — scenario names and premises are the easiest thing to change now and the most annoying to change after they're built.

---

## 8. Commercial models (GPT-4, etc.) — supported, but fenced off deliberately

Technically pluggable through the same `model_registry.py` abstraction (any OpenAI-compatible chat endpoint). Two things keep this from being a simple "just add it":

- Providers like OpenAI generally require prior written authorization for adversarial/jailbreak testing in their usage policies — this is a real contractual constraint, not a technical one, and it applies to whoever holds the key, not to us.
- Naive techniques mostly fail against frontier models anyway, so supporting them only pays off once the scenario design already includes indirect-injection and multi-turn techniques — which §7's premises are heading toward, but aren't there yet for the pilot.

**Recommendation**: ship this later as a clearly-labeled "Advanced / Bring Your Own Key" option, with an explicit on-screen note to check your own provider's usage policy first. Not part of the pilot.

---

## 9. Phased build path

1. **Shared harness** — `live/ollama_client.py` (chat, streaming, `/api/tags`), `live/model_registry.py`, config additions, startup banner. No player-facing UI yet.
2. **Mode-selection landing screen** — the Play/Live fork from §2, session-persisted.
3. **The Helpdesk Override, end to end** — one scenario, real model, streaming chat, secret-in-output verification, success banner, Learn panel. This is the pilot.
4. **Model dropdown** — once the harness is proven with one hardcoded model, generalize to the registry-driven dropdown from §4.
5. **The Ops Assistant** — introduces the sandboxed tool-calling layer and tool-call verification.
6. **The Knowledge Assistant** — introduces the vector store + retrieval-tag verification. Separate infrastructure, doesn't block on step 5.
7. **Remaining secret-in-output scenarios** — Onboarding Concierge, Compliance Copilot, Executive Briefing Bot, Report Generator — all reuse the step 1 harness directly, lowest incremental cost of the whole plan.
8. **BYOK / commercial models** — only after the above is stable.

---

## 10. Open questions for next round

- Scenario names/premises in §7 — react and revise before any of this gets built.
- Should the mode switcher in the sidebar (§2) require re-confirming Live Mode's risks/setup each time, or just silently remember the choice?
- For The Report Generator (Unbounded Consumption), what's the actual threshold that counts as "success" — a fixed token count, a wall-clock time, or something adaptive to the model's normal response length?
