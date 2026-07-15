# LLMVault — deliberately vulnerable OWASP LLM Top 10 training range.
# Made by CyberSunil.  Copyright (c) 2026 CyberSunil.  MIT License.
"""LLMVault — deliberately vulnerable OWASP LLM Top 10 training range.

Run:  python app.py   then open http://127.0.0.1:5000
For AUTHORISED security training only. Everything here is intentionally insecure.
"""
from __future__ import annotations

import datetime
import json
import os
import uuid
from flask import Flask, render_template, request, jsonify, session, Response, abort

import config
import card_svg
from challenges import load_all, get, core_labs, advanced_labs
from challenges import expert_vault

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
CHALLENGES = load_all()
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
    p = PROGRESS.setdefault(sid, {"name": "anon-" + sid[:4], "solved": {}, "hints": {},
                                  "state": {}, "expert_unlocked": False})
    p.setdefault("expert_unlocked", False)
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


# ---- completion-card content ----
REPO_DISPLAY = config.REPO_URL.replace("https://", "").replace("http://", "")
BULLETS_MASTER = ["Prompt Injection", "Data Poisoning", "Sensitive Info Disclosure",
                  "Agent Exploitation", "RAG Leakage", "Model Extraction"]
BULLETS_BEGINNER = ["Prompt Injection", "Sensitive Info Disclosure", "Supply Chain",
                    "Insecure Output", "Excessive Agency"]
DESC_MASTER = "You've completed all 20 Core & Advanced Challenges which covers.."
DESC_BEGINNER = "You've completed all 10 Core Challenges which covers.."


def share_caption(kind: str) -> str:
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
        total_ca=len(core_labs()) + len(advanced_labs()), core_n=len(core_labs()),
    )


@app.context_processor
def inject_globals():
    p = prog()
    return dict(app_name=config.APP_NAME, app_emoji=config.APP_EMOJI,
                author=config.AUTHOR, copyright=config.COPYRIGHT,
                needs_name=p["name"].startswith("anon-"),
                repo_url=config.REPO_URL)


@app.route("/")
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
    return render_template("lab.html", c=c, prog=p, score=score_of(p),
                           hints_used=p["hints"].get(cid, 0),
                           solved=cid in p["solved"], prefix=config.FLAG_PREFIX,
                           hint_costs=config.HINT_COSTS, **card_ctx(p))


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
    correct = (data.get("flag", "") or "").strip() == c.flag
    if correct and c.id not in p["solved"]:
        p["solved"][c.id] = c.max_points
        save_progress()
    return jsonify(correct=correct, score=score_of(p), solved=c.id in p["solved"],
                   defense=c.defense if correct else None,
                   core_done=core_complete(p), prereq_done=prereq_done(p))


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
    name = (request.get_json(force=True).get("name", "") or "").strip()[:10]
    if name:
        p["name"] = name
        save_progress()
        return jsonify(ok=True)
    return jsonify(ok=False, error="empty name"), 400


@app.route("/card.svg")
def card_svg_route():
    p = prog()
    if not core_complete(p):
        abort(403)
    v = request.args.get("v")
    if v not in ("master", "beginner"):
        v = "master" if prereq_done(p) else "beginner"
    if v == "master" and not prereq_done(p):
        v = "beginner"
    today = datetime.date.today().strftime("%b %d, %Y")
    if v == "master":
        svg = card_svg.render("master", "MASTER", p["name"], len(core_labs()) + len(advanced_labs()),
                              score_of(p), DESC_MASTER, BULLETS_MASTER, today,
                              REPO_DISPLAY, config.AUTHOR, config.APP_NAME)
    else:
        svg = card_svg.render("beginner", "BEGINNER", p["name"], len(core_labs()),
                              score_of(p), DESC_BEGINNER, BULLETS_BEGINNER, today,
                              REPO_DISPLAY, config.AUTHOR, config.APP_NAME)
    return Response(svg, mimetype="image/svg+xml")


@app.route("/completion")
def completion():
    p = prog()
    if not core_complete(p):
        return render_template("locked.html",
                               need_name="Core (finish the 10 core labs to earn your card)",
                               total=len(core_labs()),
                               solved=sum(1 for c in core_labs() if c.id in p["solved"]))
    variant = "master" if prereq_done(p) else "beginner"
    today = datetime.date.today().strftime("%b %d, %Y")
    if variant == "master":
        inline = card_svg.render("master", "MASTER", p["name"], len(core_labs()) + len(advanced_labs()),
                                 score_of(p), DESC_MASTER, BULLETS_MASTER, today,
                                 REPO_DISPLAY, config.AUTHOR, config.APP_NAME)
    else:
        inline = card_svg.render("beginner", "BEGINNER", p["name"], len(core_labs()),
                                 score_of(p), DESC_BEGINNER, BULLETS_BEGINNER, today,
                                 REPO_DISPLAY, config.AUTHOR, config.APP_NAME)
    return render_template("completion.html", variant=variant, score=score_of(p),
                           card_svg_inline=inline, **card_ctx(p))


@app.route("/scoreboard")
def scoreboard():
    rows = sorted(({"name": q["name"], "solved": len(q["solved"]), "score": score_of(q)}
                   for q in PROGRESS.values()), key=lambda r: r["score"], reverse=True)
    return render_template("scoreboard.html", rows=rows, total=TOTAL_LABS)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
