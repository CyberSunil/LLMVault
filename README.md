# 🔐 LLMVault

[![CI](https://github.com/CyberSunil/LLMVault/actions/workflows/ci.yml/badge.svg)](https://github.com/CyberSunil/LLMVault/actions/workflows/ci.yml)
![OWASP](https://img.shields.io/badge/OWASP-LLM%20Top%2010%20(2025)-8b5cf6)
![Labs](https://img.shields.io/badge/labs-25%20(10%20core%20%2B%2010%20advanced%20%2B%205%20expert)-ec4899)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/flask-3.x-38bdf8)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-intentionally%20vulnerable-red)

A deliberately-vulnerable, CTF-style **training range for the OWASP Top 10 for LLM Applications (2025)** — WebGoat / KubeGoat, but for AI. **25 labs across three tiers:** ten core one-per-category labs; ten **advanced, multi-turn** labs (jailbreaking, data poisoning, agent exploitation, model extraction); and five **expert** labs modelling real-world attack classes. Each tier unlocks the next.

Every lab pairs the **attack** with a **defense** (in the private solutions guide): learn the fix by practising the break.

> ⚠️ **Everything here is intentionally insecure. Authorised, self-hosted security education only.** Don't expose it to the internet or reuse its code in production.

## 📸 Screenshots

| Labs (three tiers) | A lab in action | Completion card |
|---|---|---|
| <img src="docs/labs.svg" width="300"> | <img src="docs/lab.svg" width="300"> | <img src="docs/completion-card.png" width="300"> |

<sub>Blue **Master** card = Core + Advanced complete · Green **Beginner** card = Core complete. Previews reflect the real theme; swap in your own captures anytime — see <a href="docs/README-screenshots.md">docs/</a>.</sub>


---

## 🧩 Core tier — OWASP LLM Top 10

| OWASP (2025) | Lab | Technique |
|---|---|---|
| LLM01 Prompt Injection | The Obedient Assistant | direct instruction override |
| LLM02 Sensitive Info Disclosure | Redaction Theater | output-filter bypass via encoding |
| LLM03 Supply Chain | Trust the Manifest? | typosquatted / unsigned dependency |
| LLM04 Data & Model Poisoning | The Sleeper Phrase | poisoned-data backdoor trigger |
| LLM05 Improper Output Handling | Rendered Without Question | unsanitised output → injection |
| LLM06 Excessive Agency | Keys to the Kingdom | over-permissioned tool, no authz |
| LLM07 System Prompt Leakage | Loose Lips | secret leaked from system prompt |
| LLM08 Vector & Embedding | Retrieval Without Borders | RAG retrieval ignores ACLs |
| LLM09 Misinformation | The Yes-Man | sycophancy / false authority |
| LLM10 Unbounded Consumption | Denial of Wallet | runaway generation + leaky error |

## 🔥 Advanced tier — multi-turn (unlocks after all 10 core solved)

These are **conversational**: no single message wins — they require building state across turns (roleplay escalation, iterative poisoning, tool chaining, oracle querying).

| OWASP | Lab | Advanced technique |
|---|---|---|
| LLM01 | Roleplay Unchained | **multi-turn jailbreak** via persona escalation |
| LLM02 | Death by a Thousand Hints | fragment reconstruction from a partial-disclosure oracle |
| LLM03 | The Tampered Registry | deployed-vs-canonical hash correlation |
| LLM04 | Teach Me Wrong | **active data poisoning** of an online-learning filter |
| LLM05 | The Note Keeper | **stored / second-order** injection |
| LLM06 | Confused Deputy | **agent tool-chaining** (SSRF to internal metadata) |
| LLM07 | Method Actor | multi-technique system-prompt extraction |
| LLM08 | Crossed Wires | cross-tenant RAG memory bleed |
| LLM09 | The Confident Liar | hallucination → overreliance cascade |
| LLM10 | The Oracle | **query-based model extraction** |


## ⚔️ Expert Tier — Real-World Attack Classes (unlocked after all Advanced challenges are solved)

Five **expert** labs modelling real-world, disclosed-vulnerability attack classes against LLM systems. Each is **simulated** — the app recognises the known payload and returns a flag; no real RCE/SSRF/SQL happens in the tool.

**This tier ships ENCRYPTED, and its contents are intentionally not listed here.** The challenges and flags are AES-encrypted (Fernet) into `challenges/expert.enc` with a key derived from a secret **Expert Access Key** that lives only in the operator's private vault — never in the repo. Cloning the repo yields ciphertext only; the specific scenarios stay secret until you earn them. To unlock, a player must (1) finish all Core + Advanced labs and (2) enter the key, which the operator (**CyberSunil**) hands out **manually** after the player shares their completion card. Wrong key → authenticated decryption fails → nothing is revealed.

> Discovering what's inside is part of the challenge. 🔒

---

## 🚀 Run it

```bash
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:5000
```

No API key needed — the vulnerable assistants are **deterministic/scripted**, so flags reproduce reliably and the whole range runs fully offline.

---


## 🐳 Run with Docker

```bash
# build + run
docker compose up --build          # then open http://127.0.0.1:5000
# or plain docker:
docker build -t llmvault .
docker run -p 5000:5000 llmvault
```

Served by gunicorn (single worker, so the in-memory scoreboard stays consistent).
**Do not expose this to the public internet** — it's intentionally vulnerable. To bind
to localhost only, use `"127.0.0.1:5000:5000"` in `docker-compose.yml`.


## 💾 Persistence (self-host friendly)

Progress and the scoreboard are saved to `data/progress.json` — **no database needed** — so
they survive page refresh *and* a server/container restart. In Docker the `./data` volume
keeps them across `docker compose down/up`. Delete the file to reset everyone.

## 🙋 Player experience

- **First-run name gate** (locked once set) and a **one-time guided tutorial** on your first lab.
- After you solve a lab, a **📘 Learn — the fix** panel reveals the defensive lesson for that OWASP category.
- **Responsive layout** — works on phones (the sidebar collapses, panels stack).

## 🕹️ How to play

1. On first launch you set a **player name** (locked once chosen — it can't be changed after).
2. Work the **core** labs; make each assistant leak its flag using that category's technique.
3. Clear all 10 core labs to unlock the **advanced tier**; clear all advanced to unlock the **expert tier**.
4. Reveal **hints** if stuck (−5 pts each). Submit flags (`LLMVAULT{...}`, configurable in `config.py`).
5. Cards **float on hover** and turn **green when solved**; track everything on the **Scoreboard**.

**Scoring:** core 100–300 pts, advanced 400, expert 500; hints cost 10 / 25 / 50 (escalating).

---


## 🎓 Completion card & sharing

Two milestone cards unlock automatically as a pop-up the moment you finish a tier:
a **green Beginner** card (all 10 Core labs) and a **blue Master** card (all 20 Core +
Advanced). Both are also at `/completion`. Each has a **Download card (PNG/SVG)** button,
a pre-written caption (Copy), and LinkedIn/X openers.

**Sharing an image:** social sites can't auto-attach an image from a share link, so the
flow is: **Download the card → open LinkedIn/X → paste the caption → attach the image.**
Players post it and tag **CyberSunil** to receive the Expert Access Key. The card renders
server-side as a themed SVG (`/card.svg`) and exports to PNG in-browser — no external deps.

## 🧱 Architecture

```
app.py                      # Flask: labs, chat, hint, submit, scoreboard, name-gate, unlock gating
config.py                   # APP_NAME, AUTHOR/COPYRIGHT, flag prefix, scoring
challenges/
  __init__.py               # Challenge base (tier), registry, core_labs()/advanced_labs()
  llm01_..llm10_*.py         # core labs
  advanced/a01_..a10_*.py    # advanced multi-turn labs
  expert.enc                 # ENCRYPTED expert tier (ciphertext, shipped)
  expert_meta.json           # public KDF salt/params
  expert_vault.py            # runtime decryptor + declarative challenge engine
templates/  static/          # dark violet UI + completion card + expert key gate
Dockerfile  docker-compose.yml  # containerised deploy
LICENSE                     # MIT + security notice
SOLUTIONS.md                # 🔒 all 20 flags + walkthroughs + defenses (git-ignored)
```

Each challenge is a `Challenge` subclass with a `respond(message, state)` that encodes the vuln; advanced labs use the persistent `state` dict for multi-turn logic. Add your own by dropping a module in `challenges/` (or `challenges/advanced/`) and registering it.

---

## 👤 Credit & license

Made by **CyberSunil**. © 2026 CyberSunil. Released under the **MIT License** (see `LICENSE`), with a security notice that the project is deliberately vulnerable and for authorised training only. The author credit is shown on every page and is not runtime-editable.

---

*Break it here so you can defend it everywhere.*

---

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Security policy: [SECURITY.md](SECURITY.md).
