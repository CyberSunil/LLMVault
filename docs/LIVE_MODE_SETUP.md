# Live Mode — Setup

Live Mode replaces LLMVault's scripted bots with a **real model running on your
own machine**. Nothing is deterministic: the assistant genuinely has to be
out-thought, and the target secret is generated per session, so there is no
answer to look up.

Play Mode is unaffected by everything on this page. If you skip this setup, the
Live Zone shows these instructions instead of labs and the rest of LLMVault
works exactly as before.

---

## 1. Install Ollama

Grab it from **https://ollama.com** (macOS, Linux, Windows).

Verify it's serving:

```bash
curl http://localhost:11434/api/tags
```

A JSON response means you're good. Connection refused means it isn't running —
start it with `ollama serve`.

## 2. Pull the tuned model

```bash
ollama pull qwen2.5:3b-instruct
```

**~2 GB on disk, runs on CPU, no GPU required.** Expect roughly 5–20 tokens/sec
on a typical laptop CPU, so replies take a few seconds. That's normal — Live
Mode streams token-by-token so you can watch it think rather than staring at a
spinner.

## 3. Start LLMVault

```bash
python app.py
```

You'll see a preflight banner before Flask starts:

```
  LLMVault — Live Mode preflight
    Ollama    : detected at http://localhost:11434  (1 model)
                  - qwen2.5:3b-instruct
    OpenAI    : not configured (optional; set OPENAI_API_KEY)
    Live Mode : READY
```

Open the app, choose **Live Mode**, and pick a scenario.

---

## Configuration

All optional — sensible defaults are built in. Override via environment
variables:

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Where Ollama listens. In Docker try `http://host.docker.internal:11434`. |
| `OLLAMA_DEFAULT_MODEL` | `qwen2.5:3b-instruct` | Pre-selected in the model dropdown. |
| `OLLAMA_TIMEOUT` | `180` | Seconds to wait for a full reply. Raise it on slow hardware. |
| `OPENAI_API_KEY` | unset | If set, OpenAI models appear in the dropdown. See the caveat below. |

---

## Choosing a model

The shipped scenario prompt was written against **`qwen2.5:3b-instruct`**. Other
models will work, but difficulty is only calibrated for that one — swap it and a
scenario may become trivial or effectively impossible.

Some honest guidance if you want to experiment:

- **Too well-aligned** (refuses everything) makes for a frustrating lab, not a
  hard one. If nothing works after genuine effort, try a different model before
  assuming you're missing something.
- **Too compliant** (leaks on the first polite ask) teaches nothing.
- The sweet spot is a model that refuses the obvious approach and yields to a
  well-constructed one.

Reasonable alternatives to try: `llama3.2:3b`, `gemma2:2b` (smaller/faster,
rougher output), `mistral:7b` (needs more RAM).

If you want to evaluate a model's resistance systematically rather than by feel,
the open-source **`ollama-says`** project runs a multi-attack suite against local
models and is a better basis for a decision than any single benchmark number.

---

## Using commercial models (optional)

Setting `OPENAI_API_KEY` adds OpenAI models to the dropdown.

**Read your provider's usage policy first.** Providers generally require prior
authorization for adversarial or jailbreak testing, and that obligation sits
with whoever owns the key — not with LLMVault. This is a contractual question,
not a technical one.

Practically: frontier models shrug off the simpler techniques, so the shipped
scenario will mostly just refuse. It's there for comparison — seeing the same
attack succeed locally and fail against a frontier model is itself a good
lesson about how much alignment training actually does.

---

## How scoring works (it doesn't)

Live Mode has **no points, no flags, and no hint costs**. Success is a single
objective per scenario: get the assistant to do the thing it was told not to do.
When it happens, the app detects it from the model's own output and shows you
the fix.

Hints are free and unlimited. There's no score to protect, so there's no reason
to charge for curiosity.

---

## Troubleshooting

**"Ollama not detected"** — check `curl http://localhost:11434/api/tags`. If that
works but LLMVault disagrees, you're probably running LLMVault in a container;
set `OLLAMA_HOST=http://host.docker.internal:11434`.

**"Model X is not pulled"** — `ollama pull X`, then reload.

**Replies are very slow** — expected on CPU. Try a smaller model (`gemma2:2b`)
or raise `OLLAMA_TIMEOUT`.

**The model produces nonsense** — small models do this occasionally. Hit
**Reset** to clear the conversation; the target secret stays the same, so you
aren't restarting the challenge.

**Nothing I try works** — that may be the model, not you. See "Choosing a model".
