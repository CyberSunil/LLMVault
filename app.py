# LLMVault — deliberately vulnerable OWASP LLM Top 10 training range.
# Made by CyberSunil.  Copyright (c) 2026 CyberSunil.  MIT License.
"""LLMVault — deliberately vulnerable OWASP LLM Top 10 training range.

Run:  python app.py   then open http://127.0.0.1:5000
For AUTHORISED security training only. Everything here is intentionally insecure.
"""
from __future__ import annotations

import datetime
import hashlib
import hmac
import json
import os
import uuid
from flask import (Flask, render_template, request, jsonify, session, Response,
                   abort, stream_with_context)

import config
import card_svg
from challenges import load_all, get, core_labs, advanced_labs
from challenges import expert_vault
from owasp_notes import OWASP_NOTES

import live
from live import model_registry
from live.ollama_client import OllamaError, chat_stream

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
CHALLENGES = load_all()
live.load_all()
TOTAL_LABS = len(CHALLENGES) + expert_vault.expert_count()

# ---------------- persistence (JSON file — survives refresh AND restart) ---------
PROGRESS: dict[str, dict] = {}


def _load_progress():
    global PROGRESS
    try:
        with open(config.DATA_FILE) as fh:
            PROGRESS = json.load(fh)
    except (FileNotFoundError, ValueError):
        PROGRESS = {}


def save_progress():
    os.makedirs(os.path.dirname(config.DATA_FILE) or ".", exist_ok=True)
    tmp = config.DATA_FILE + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(PROGRESS, fh)
    os.replace(tmp, config.DATA_FILE)


_load_progress()


def prog() -> dict:
    sid = session.get("sid")
    if not sid:
        sid = session["sid"] = uuid.uuid4().hex
    p = PROGRESS.setdefault(sid, {"name": "anon-" + sid[:4], "role": "", "solved": {}, "hints": {},
                                  "state": {}, "expert_unlocked": False})
    p.setdefault("expert_unlocked", False)
    p.setdefault("expert_cleared", False)
    p.setdefault("role", "")
    return p


def hint_penalty(used: int) -> int:
    costs = config.HINT_COSTS
    return sum(costs[min(i, len(costs) - 1)] for i in range(used))


def score_of(p: dict) -> int:
    return sum(p["solved"].values()) - sum(hint_penalty(n) for n in p["hints"].values())


def tier_complete(p: dict, t: int) -> bool:
    labs = {1: core_labs, 2: advanced_labs}.get(t)
    if labs is None:
        return all(c.id in p["solved"] for c in expert_vault.all_expert())
    return all(c.id in p["solved"] for c in labs())


def core_complete(p): return tier_complete(p, 1)
def prereq_done(p): return tier_complete(p, 1) and tier_complete(p, 2)


def expert_complete(p) -> bool:
    """All Expert Vault labs solved.

    Two wrinkles this has to survive:

    1. tier_complete() delegates to all_expert(), which is an empty list while
       the vault is locked — and all([]) is True. So the count is checked.
    2. The decrypted specs live in memory only (expert_vault._SPECS), so after
       an app restart all_expert() is empty again even though the solves are
       still in progress.json. Without a latch the purple certificate would
       silently downgrade to blue. Once earned, it is recorded permanently.
    """
    if p.get("expert_cleared"):
        return True
    n = expert_vault.expert_count()
    if not n or not expert_vault.is_loaded():
        return False
    if sum(1 for c in expert_vault.all_expert() if c.id in p["solved"]) == n:
        p["expert_cleared"] = True
        save_progress()
        return True
    return False


# ---- completion-card content ----
REPO_DISPLAY = config.REPO_URL.replace("https://", "").replace("http://", "")
BULLETS_MASTER = ["Prompt Injection", "Data Poisoning", "Sensitive Info Disclosure",
                  "Agent Exploitation", "RAG Leakage", "Model Extraction"]
BULLETS_BEGINNER = ["Prompt Injection", "Sensitive Info Disclosure", "Supply Chain",
                    "Insecure Output", "Excessive Agency"]
DESC_MASTER = "You've completed all 20 Core & Advanced Challenges which covers.."
DESC_BEGINNER = "You've completed all 10 Core Challenges which covers.."
BULLETS_EXPERT_FALLBACK = ["SSRF", "SSTI / RCE", "Indirect Injection",
                           "Multi-Agent Exploitation", "Text-to-SQL"]
DESC_EXPERT = "You've cleared the full vault — Core, Advanced & Expert — which covers.."


def bullets_expert():
    """Expert bullets come from the real Expert labs once the vault is unlocked.

    While it is still locked the titles are not readable, so fall back to the
    Master list rather than inventing lab names.
    """
    cats = []
    for c in expert_vault.all_expert():
        label = (c.owasp.split(":", 1)[-1] or "").strip()
        label = label.split(" ", 1)[-1] if label[:4].isdigit() else label
        if label and label not in cats:
            cats.append(label)
    return cats[:6] or BULLETS_EXPERT_FALLBACK


def share_caption(kind: str) -> str:
    if kind == "expert":
        body = ("the entire LLMVault Expert Vault \U0001f513 \u2014 all 25 Core, Advanced "
                "and Expert labs of a hands-on OWASP LLM Top 10 (2025) attack range.")
        tags = "#AISecurity #LLMSecurity #OWASP #RedTeam #PromptInjection"
        return (f"I just completed {body}\n\n\u2b50 Try LLMVault: {config.REPO_URL} "
                f"If you find it useful, consider giving it a star.\n{tags}")
    if kind == "master":
        body = ("all 20 Core & Advanced labs of LLMVault \U0001f513 — a hands-on OWASP LLM "
                "Top 10 (2025) attack range: prompt injection, data poisoning, agent "
                "exploitation, RAG leakage, model extraction & more.")
        tags = "#AISecurity #LLMSecurity #OWASP #RedTeam #PromptInjection"
    else:
        body = ("all 10 Core labs of LLMVault \U0001f513 — the OWASP LLM Top 10 (2025) "
                "fundamentals: prompt injection, sensitive info disclosure, insecure "
                "output handling & more.")
        tags = "#AISecurity #LLMSecurity #OWASP"
    return (f"I just completed {body}\n\n\u2b50 Try LLMVault: {config.REPO_URL} "
            f"If you find it useful, consider giving it a star.\n{tags}")


def expert_access(p) -> bool:
    return prereq_done(p) and p.get("expert_unlocked") and expert_vault.is_loaded()


def find(cid):
    return get(cid) or expert_vault.get_expert(cid)


def can_access(c, p) -> bool:
    if c.tier <= 2:
        return all(tier_complete(p, t) for t in range(1, c.tier))
    return expert_access(p)


def card_ctx(p) -> dict:
    return dict(
        player_name=p["name"],
        today=datetime.date.today().strftime("%b %d, %Y"),
        repo_display=REPO_DISPLAY, repo=config.REPO_URL,
        bullets_master=BULLETS_MASTER, bullets_beginner=BULLETS_BEGINNER,
        desc_master=DESC_MASTER, desc_beginner=DESC_BEGINNER,
        cap_master=share_caption("master"), cap_beginner=share_caption("beginner"),
        cap_expert=share_caption("expert"),
        total_ca=len(core_labs()) + len(advanced_labs()), core_n=len(core_labs()),
    )


@app.context_processor
def inject_globals():
    p = prog()
    return dict(app_name=config.APP_NAME, app_emoji=config.APP_EMOJI,
                author=config.AUTHOR, copyright=config.COPYRIGHT,
                needs_name=p["name"].startswith("anon-"),
                player_name=p["name"], player_role=p.get("role", ""),
                nav_solved=len(p.get("solved", {})),
                nav_total=len(core_labs()) + len(advanced_labs()),
                nav_badges=badge_row(p),
                repo_url=config.REPO_URL)


def recent_activity(p, limit=4):
    """Real recent-activity feed across BOTH modes — no fabricated entries.

    Play solves (dict insertion order tracks solve order) and Live solves (which
    carry a real won_on timestamp) are merged; timestamped Live wins sort by time,
    Play wins fall back to solve order. Fills any remaining slots with one
    in-progress entry per mode (a lab/scenario chatted with but not yet solved).
    """
    done = []
    # Live solves — real timestamps
    for sid, lv in p.get("live", {}).items():
        if lv.get("solved"):
            sc = live.get(sid)
            if sc:
                done.append({"title": sc.title, "owasp": sc.owasp, "status": "done",
                             "mode": "live", "points": None, "ts": lv.get("won_on") or "",
                             "_order": 0})
    # Play solves — insertion order stands in for time
    play_solved = list(p.get("solved", {}).keys())
    for i, cid in enumerate(play_solved):
        c = find(cid)
        if c:
            done.append({"title": c.title, "owasp": c.owasp, "status": "done",
                         "mode": "play", "points": p["solved"][cid], "ts": "", "_order": i})
    # timestamped (Live) first by time desc, then Play by reverse solve order
    done.sort(key=lambda d: (d["ts"], d["_order"]), reverse=True)
    items = [{k: v for k, v in d.items() if k != "_order"} for d in done[:limit]]

    # fill remaining slots with in-progress: one Play, one Live
    if len(items) < limit:
        for cid in p.get("state", {}):
            if cid not in p.get("solved", {}):
                c = find(cid)
                if c:
                    items.append({"title": c.title, "owasp": c.owasp, "points": c.max_points,
                                 "status": "progress", "mode": "play"})
                break
    if len(items) < limit:
        for sid, lv in p.get("live", {}).items():
            if not lv.get("solved") and lv.get("history"):
                sc = live.get(sid)
                if sc:
                    items.append({"title": sc.title, "owasp": sc.owasp, "points": None,
                                 "status": "progress", "mode": "live"})
                break
    return items[:limit]


# ---------------- Dashboard (Mission Command) ------------------------------
# Everything the dashboard shows is derived from real progress. Nothing on that
# page is decorative-with-fake-numbers: if there is no data yet, the panel says
# so rather than inventing a plausible-looking value.

# Thresholds are spaced against the real points pool (Core 2400 + Advanced 4000).
RANKS = [("Initiate", 0), ("Apprentice", 400), ("Adept", 1200),
         ("Operator", 2400), ("Specialist", 4000), ("Vault Master", 6400)]


def rank_info(score: int) -> dict:
    """Current rank, the next one up, and how far through the band we are."""
    s = max(0, score)
    idx = 0
    for i, (_, floor) in enumerate(RANKS):
        if s >= floor:
            idx = i
    name, floor = RANKS[idx]
    if idx + 1 < len(RANKS):
        nxt, ceil = RANKS[idx + 1]
        span = ceil - floor
        pct = round(((s - floor) / span) * 100) if span else 100
    else:
        nxt, ceil, pct = None, floor, 100
    return {"name": name, "next": nxt, "at": s, "goal": ceil, "tier": idx + 1,
            "art": f"rank-{idx + 1}", "of": len(RANKS),
            "pct": max(0, min(100, pct))}


def tier_rows(p: dict) -> list[dict]:
    """Per-tier completion — the dashboard's four-meter overview."""
    solved = p.get("solved", {})
    live_solved = sum(1 for v in p.get("live", {}).values() if v.get("solved"))
    rows = [
        {"key": "CORE LABS", "done": sum(1 for c in core_labs() if c.id in solved),
         "total": len(core_labs()), "tone": ""},
        {"key": "ADVANCED", "done": sum(1 for c in advanced_labs() if c.id in solved),
         "total": len(advanced_labs()), "tone": "y"},
        {"key": "EXPERT VAULT", "done": sum(1 for c in expert_vault.all_expert()
                                            if c.id in solved),
         "total": expert_vault.expert_count(), "tone": "c"},
        {"key": "LIVE ZONE", "done": live_solved,
         "total": len(live.all_scenarios()), "tone": "g"},
    ]
    for r in rows:
        r["pct"] = round(r["done"] / r["total"] * 100) if r["total"] else 0
        r["cells"] = round(r["pct"] / 100 * 12)
    return rows


def badge_row(p: dict) -> list[dict]:
    """One badge per tier, matching the three certificates exactly.

    Cumulative on purpose: the tiers are strictly gated (Advanced is only
    reachable once Core is cleared, Expert once both are), so holding a higher
    badge implies every badge below it. Clearing Advanced therefore lights up
    Core *and* Advanced rather than looking like Core was skipped.
    """
    core_ok = core_complete(p)
    adv_ok = tier_complete(p, 2)
    exp_ok = expert_complete(p)
    if exp_ok:
        adv_ok = core_ok = True
    if adv_ok:
        core_ok = True
    return [
        {"key": "core", "short": "Core", "label": "Core Complete", "art": "badge-1",
         "sub": f"{len(core_labs())} core labs", "earned": core_ok},
        {"key": "advanced", "short": "Advanced", "label": "Advanced Complete", "art": "badge-2",
         "sub": f"{len(advanced_labs())} advanced labs", "earned": adv_ok},
        {"key": "expert", "short": "Expert", "label": "Expert Vault", "art": "badge-expert",
         "sub": f"{expert_vault.expert_count()} expert labs", "earned": exp_ok},
    ]


@app.route("/api/time")
def api_time():
    """Wall clock of the host the app is served from, not the browser's."""
    now = datetime.datetime.now().astimezone()
    off = now.utcoffset() or datetime.timedelta(0)
    return jsonify(epoch=now.timestamp(), tz=now.tzname() or "LOCAL",
                   offset_min=int(off.total_seconds() // 60))


@app.route("/")
def welcome():
    p = prog()
    rows = tier_rows(p)
    done = sum(r["done"] for r in rows)
    total = sum(r["total"] for r in rows)
    return render_template(
        "welcome.html", prog=p, score=score_of(p),
        activity=recent_activity(p, limit=12),
        rank=rank_info(score_of(p)), tiers=rows,
        badges=badge_row(p),
        overall_done=done, overall_total=total,
        overall_pct=round(done / total * 100) if total else 0,
        live_total=len(live.all_scenarios()),
        ollama_host=getattr(config, "OLLAMA_HOST", ""),
        store_ok=os.access(os.path.dirname(os.path.abspath(config.DATA_FILE)) or ".", os.W_OK),
        store_file=config.DATA_FILE,
        store_sessions=len(PROGRESS),
        ollama_model=getattr(config, "OLLAMA_DEFAULT_MODEL", ""),
        expert_unlocked=bool(p.get("expert_unlocked")),
        expert_loaded=expert_vault.is_loaded(),
        expert_count=expert_vault.expert_count(),
        core_n=len(core_labs()), adv_n=len(advanced_labs()),
        points_pool=sum(c.max_points for c in core_labs())
        + sum(c.max_points for c in advanced_labs()),
        flag_prefix=getattr(config, "FLAG_PREFIX", ""),
        author_handle=getattr(config, "AUTHOR_HANDLE", config.AUTHOR),
        ranks=[{"name": n, "at": t} for n, t in RANKS],
    )


# ---------------- Live Mode ------------------------------------------------
# Real local models instead of scripted bots. Kept deliberately separate from
# Play Mode: no points, no flag box, per-session secrets, and progress stored
# under its own key so it can never affect the Play Mode scoreboard.

def live_state(p: dict, sid: str) -> dict:
    return p.setdefault("live", {}).setdefault(
        sid, {"history": [], "solved": False, "hints": 0, "won_on": None})


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


@app.route("/live")
def live_zone():
    p = prog()
    info = model_registry.discover()
    lv = p.get("live", {})
    return render_template("live_zone.html", prog=p, score=score_of(p),
                           scenarios=live.all_scenarios(), info=info,
                           solved={k for k, v in lv.items() if v.get("solved")})


@app.route("/live/<sid>")
def live_lab(sid):
    sc = live.get(sid)
    if not sc:
        return "No such live scenario", 404
    p = prog()
    st = live_state(p, sid)
    info = model_registry.discover()
    return render_template("live_lab.html", sc=sc, prog=p, info=info,
                           default_model=model_registry.default_model(info),
                           history=st["history"], solved=st["solved"],
                           hints_used=st["hints"],
                           secret_hint=live.session_secret(session["sid"], sid)[:4] + "…")


@app.route("/api/live/status")
def live_status():
    return jsonify(model_registry.discover())


@app.route("/api/live/hint", methods=["POST"])
def live_hint():
    """Free and unlimited — Live Mode has no score to protect, so gating hints
    behind a cost would only punish curiosity."""
    data = request.get_json(force=True)
    sc = live.get(data.get("sid", ""))
    if not sc:
        return jsonify(error="no such scenario"), 404
    idx = data.get("index", 0)
    if not isinstance(idx, int) or not (0 <= idx < len(sc.hints)):
        return jsonify(error="no such hint"), 400
    p = prog()
    st = live_state(p, sc.id)
    st["hints"] = max(st["hints"], idx + 1)
    save_progress()
    return jsonify(hint=sc.hints[idx], used=st["hints"], total=len(sc.hints))


@app.route("/api/live/reset", methods=["POST"])
def live_reset():
    """Clear the conversation but keep the same session secret, so a reset is a
    fresh attempt at the same target rather than a different puzzle."""
    data = request.get_json(force=True)
    sc = live.get(data.get("sid", ""))
    if not sc:
        return jsonify(error="no such scenario"), 404
    p = prog()
    st = live_state(p, sc.id)
    st["history"] = []
    save_progress()
    return jsonify(ok=True)


@app.route("/api/live/chat", methods=["POST"])
def live_chat():
    """Streamed turn against a real model, verified on the way past.

    Returns Server-Sent Events rather than one JSON blob because CPU inference
    on a small model runs at roughly 5-20 tokens/sec — a blocking request would
    leave the UI frozen for 10-30 seconds per message.
    """
    data = request.get_json(force=True)
    sc = live.get(data.get("sid", ""))
    if not sc:
        return jsonify(error="no such scenario"), 404
    msg = (data.get("message") or "").strip()
    attachment = (data.get("attachment") or "")
    att_name = (data.get("attachment_name") or "notes.txt")
    image_b64 = (data.get("image") or "")
    image_name = (data.get("image_name") or "screenshot.png")
    # Cap the uploaded document. This is a training doc, not a data pipeline, and
    # an unbounded blob would only bloat the model's context and the saved history.
    if attachment and len(attachment) > 20000:
        attachment = attachment[:20000] + "\n…[truncated]"

    # Decode + extract text from an uploaded image (indirect injection channel).
    image_texts = None
    if image_b64:
        import base64
        try:
            raw = base64.b64decode(image_b64.split(",")[-1])
        except Exception:
            raw = b""
        if len(raw) > 2 * 1024 * 1024:
            return jsonify(error="Image too large (max 2 MB)."), 400
        from live import image_probe
        if not image_probe.sniff(raw):
            return jsonify(error="That file doesn't look like a supported image."), 400
        image_texts = image_probe.extract_text(raw)

    if not msg and not attachment and not image_b64:
        return jsonify(error="empty message"), 400
    if not msg and attachment:
        msg = f"Please turn the attached notes ({att_name}) into a report."
    if not msg and image_b64:
        msg = f"Here's a screenshot of my issue ({image_name}) — can you help?"

    info = model_registry.discover()
    model = data.get("model") or model_registry.default_model(info)
    if not model:
        return jsonify(error="No model available. Is Ollama running?"), 503

    p = prog()
    st = live_state(p, sc.id)
    secret = live.session_secret(session["sid"], sc.id)
    # An uploaded file becomes a <document> block appended to the turn. This is
    # the realistic indirect-injection surface: the payload rides inside content
    # the assistant was asked to process, not inside the chat instruction.
    user_content = msg
    if attachment:
        user_content = (f"{msg}\n\n<document filename=\"{att_name}\">\n"
                        f"{attachment}\n</document>")
    if image_b64:
        from live import image_probe
        block = image_probe.as_context_block(image_name, image_texts or [])
        user_content = f"{msg}\n\n{block}"
    st["history"].append({"role": "user", "content": user_content})
    messages = sc.build_messages(secret, st["history"])
    host = config.OLLAMA_HOST

    def generate():
        full = ""
        try:
            for piece in chat_stream(host, model, messages,
                                     timeout=config.OLLAMA_TIMEOUT):
                full += piece
                yield _sse({"delta": piece})
        except OllamaError as e:
            # roll the unanswered user turn back out of history so a retry
            # doesn't replay it twice to the model
            if st["history"] and st["history"][-1]["role"] == "user":
                st["history"].pop()
            save_progress()
            yield _sse({"error": str(e)})
            return

        st["history"].append({"role": "assistant", "content": full})
        newly_solved = False
        if not st["solved"] and sc.verify(full, secret, st):
            st["solved"] = True
            st["won_on"] = datetime.datetime.now().isoformat(timespec="seconds")
            newly_solved = True
        save_progress()

        # Scenarios with a downstream engine (LLM05 family) return the rendered
        # output so the UI can show it. This is where the leak is actually visible
        # — the chat reply may just contain a placeholder; the render resolves it.
        rendered = sc.render(full, secret)
        yield _sse({"done": True, "solved": st["solved"], "newly_solved": newly_solved,
                    "rendered": rendered,
                    "secret": secret if st["solved"] else None,
                    "defense": sc.defense if st["solved"] else None})

    return Response(stream_with_context(generate()),
                    mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/play")
def labs():
    p = prog()
    expert = expert_vault.all_expert() if expert_access(p) else []
    return render_template("labs.html", core=core_labs(), advanced=advanced_labs(),
                           expert=expert, prog=p, score=score_of(p),
                           core_done=core_complete(p), advanced_done=tier_complete(p, 2),
                           prereq_done=prereq_done(p), expert_unlocked=expert_access(p),
                           expert_count=expert_vault.expert_count(),
                           core_count=len(core_labs()), advanced_count=len(advanced_labs()),
                           prefix=config.FLAG_PREFIX)


@app.route("/lab/<cid>")
def lab(cid):
    c = find(cid)
    if not c:
        return "No such lab", 404
    p = prog()
    if not can_access(c, p):
        if c.tier == 3 and prereq_done(p):
            return render_template("locked.html", need_name="Expert (enter the access key on the Labs page)",
                                   total=expert_vault.expert_count(), solved=0)
        tier_names = {1: "Core", 2: "Advanced"}
        need = next((t for t in (1, 2, 3) if not tier_complete(p, t)), 1)
        pool = core_labs() if need == 1 else (advanced_labs() if need == 2 else [])
        return render_template("locked.html", need_name=tier_names.get(need, "prior"),
                               total=len(pool) or expert_vault.expert_count(),
                               solved=sum(1 for x in pool if x.id in p["solved"]))
    owasp_code = c.owasp.split(":", 1)[0].strip() if c.owasp else ""
    return render_template("lab.html", c=c, prog=p, score=score_of(p),
                           hints_used=p["hints"].get(cid, 0),
                           solved=cid in p["solved"], prefix=config.FLAG_PREFIX,
                           hint_costs=config.HINT_COSTS,
                           owasp_note=OWASP_NOTES.get(owasp_code),
                           **card_ctx(p))


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    c = find(data.get("cid", ""))
    if not c:
        return jsonify(error="no such lab"), 404
    p = prog()
    if not can_access(c, p):
        return jsonify(error="locked"), 403
    msg = data.get("message", "")
    state = p.setdefault("state", {}).setdefault(c.id, {})
    reply = c.respond(msg, state)
    save_progress()
    return jsonify(reply=reply, render_html=c.render_html)


@app.route("/api/hint", methods=["POST"])
def hint():
    data = request.get_json(force=True)
    c = find(data.get("cid", ""))
    if not c:
        return jsonify(error="no such lab"), 404
    p = prog()
    if not can_access(c, p):
        return jsonify(error="locked"), 403
    idx = data.get("index", 0)
    if not isinstance(idx, int) or idx < 0 or idx >= len(c.hints):
        return jsonify(error="no such hint"), 400
    used = p["hints"].get(c.id, 0)
    if idx > used:
        # can't skip ahead — hints must be revealed in order
        return jsonify(error="reveal the earlier hints first"), 403
    if idx == used and c.id not in p["solved"]:
        p["hints"][c.id] = used + 1
        save_progress()
    return jsonify(hint=c.hints[idx], score=score_of(p), used=p["hints"].get(c.id, 0))


@app.route("/api/submit", methods=["POST"])
def submit():
    data = request.get_json(force=True)
    c = find(data.get("cid", ""))
    if not c:
        return jsonify(error="no such lab"), 404
    p = prog()
    if not can_access(c, p):
        return jsonify(error="locked"), 403
    submitted = (data.get("flag", "") or "").strip()
    submitted_hash = hashlib.sha256(submitted.encode()).hexdigest()
    correct = hmac.compare_digest(submitted_hash, c.flag_hash)
    if correct and c.id not in p["solved"]:
        p["solved"][c.id] = c.max_points
        save_progress()
    return jsonify(correct=correct, score=score_of(p), solved=c.id in p["solved"],
                   defense=c.defense if correct else None,
                   core_done=core_complete(p), prereq_done=prereq_done(p),
                   advanced_done=tier_complete(p, 2),
                   expert_done=expert_complete(p),
                   badges=badge_row(p))


@app.route("/api/unlock-expert", methods=["POST"])
def unlock_expert():
    p = prog()
    if not prereq_done(p):
        return jsonify(ok=False, error="Finish all Core and Advanced labs first."), 403
    key = (request.get_json(force=True).get("key", "") or "").strip()
    if not key:
        return jsonify(ok=False, error="Enter the access key."), 400
    if expert_vault.try_unlock(key):
        p["expert_unlocked"] = True
        save_progress()
        return jsonify(ok=True, count=expert_vault.expert_count())
    return jsonify(ok=False, error="Invalid access key."), 403


@app.route("/api/setname", methods=["POST"])
def setname():
    p = prog()
    if not p["name"].startswith("anon-"):
        return jsonify(ok=False, error="name is locked"), 403
    data = request.get_json(force=True)
    name = (data.get("name", "") or "").strip()[:14]
    role = (data.get("role", "") or "").strip()[:24]
    if name:
        p["name"] = name
        if role:
            p["role"] = role
        save_progress()
        return jsonify(ok=True)
    return jsonify(ok=False, error="empty name"), 400


@app.route("/api/setrole", methods=["POST"])
def setrole():
    p = prog()
    if p["name"].startswith("anon-"):
        return jsonify(ok=False, error="set a name first"), 400
    role = (request.get_json(force=True).get("role", "") or "").strip()[:24]
    if role:
        p["role"] = role
        save_progress()
        return jsonify(ok=True, role=role)
    return jsonify(ok=False, error="empty role"), 400


CARD_SPECS = {
    "expert":   ("EXPERT",   lambda: len(core_labs()) + len(advanced_labs())
                 + expert_vault.expert_count(), DESC_EXPERT, bullets_expert),
    "master":   ("MASTER",   lambda: len(core_labs()) + len(advanced_labs()),
                 DESC_MASTER, lambda: BULLETS_MASTER),
    "beginner": ("BEGINNER", lambda: len(core_labs()),
                 DESC_BEGINNER, lambda: BULLETS_BEGINNER),
}


def card_variant(p) -> str:
    """Highest card the player has actually earned."""
    if expert_complete(p):
        return "expert"
    return "master" if prereq_done(p) else "beginner"


def render_card(p, variant: str) -> str:
    level, count, desc, bullets = CARD_SPECS[variant]
    return card_svg.render(variant, level, p["name"], count(), score_of(p),
                           desc, bullets(),
                           datetime.date.today().strftime("%b %d, %Y"),
                           REPO_DISPLAY, config.AUTHOR, config.APP_NAME)


@app.route("/card.svg")
def card_svg_route():
    p = prog()
    if not core_complete(p):
        abort(403)
    earned = card_variant(p)
    v = request.args.get("v")
    if v not in CARD_SPECS:
        v = earned
    # never hand out a tier the player has not reached
    rank_order = ["beginner", "master", "expert"]
    if rank_order.index(v) > rank_order.index(earned):
        v = earned
    return Response(render_card(p, v), mimetype="image/svg+xml")


@app.route("/completion")
def completion():
    p = prog()
    if not core_complete(p):
        return render_template("locked.html",
                               need_name="Core (finish the 10 core labs to earn your card)",
                               total=len(core_labs()),
                               solved=sum(1 for c in core_labs() if c.id in p["solved"]))
    variant = card_variant(p)
    return render_template("completion.html", variant=variant, score=score_of(p),
                           card_svg_inline=render_card(p, variant), **card_ctx(p))


@app.route("/scoreboard")
def scoreboard():
    rows = sorted(({"name": q["name"], "solved": len(q["solved"]), "score": score_of(q)}
                   for q in PROGRESS.values()), key=lambda r: r["score"], reverse=True)
    return render_template("scoreboard.html", rows=rows, total=TOTAL_LABS)


if __name__ == "__main__":
    if getattr(config, "LIVE_MODE_ENABLED", False):
        print(model_registry.startup_banner())
    app.run(host="127.0.0.1", port=5000, debug=True)
