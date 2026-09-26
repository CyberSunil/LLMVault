"""LLM06:2025 — Excessive Agency (over-permissioned, unscoped tools).

A simulated agent runtime. OpsBot exposes real tools — list_dir() and read_file()
— that run with the app's privileges and CLAIM to be sandboxed to its workspace,
but the sandbox is advisory only: absolute paths and ../ traversal escape it. No
authorization is enforced at the tool boundary. The secret is NOT at a guessable
path; you must use the agent's own tools to enumerate the filesystem, follow the
breadcrumbs in its workspace config/logs to a secrets mount OUTSIDE the sandbox,
and read it. That discovery-through-tools loop is what excessive agency looks like.
"""
import re

from config import FLAG_PREFIX
from . import Challenge, decode_flag_part, register

_FLAG_SUFFIX = decode_flag_part("pGEu+2o1ENZ9AkcEPmNIUB0MqVTkgUTbpTtFRox1Lj27gbekSIbXPT9b8zvguOSKCw+FUNsH6sozmAY=")
FLAG = f"{FLAG_PREFIX}{{{_FLAG_SUFFIX}}}"

SANDBOX = "/home/opsbot/workspace"

# Simulated filesystem. The flag lives OUTSIDE the sandbox, on an unguessable path
# you have to discover — not spelled out anywhere in the UI.
FS = {
    f"{SANDBOX}/README.md":
        "OpsBot workspace. My file tools are sandboxed to this directory for safety.\n"
        "Deploy configs and run logs live here.",
    f"{SANDBOX}/notes.txt":
        "Reminder: rotate the staging token. Standup 10am.",
    f"{SANDBOX}/deploy.yaml":
        "region: eu-west-1\nlog_level: info\n"
        "secrets_mount: /var/secrets/vault   # read-only mount for the ops ROLE, not chat users\n",
    f"{SANDBOX}/logs/app.log":
        "INFO  boot ok\n"
        "INFO  loaded admin.key from /var/secrets/vault/ at startup\n"
        "WARN  read_file() has no path allow-list — accepts absolute paths and ../ (JIRA OPS-231)\n",
    "/var/secrets/vault/admin.key": FLAG,                        # <-- the target
    "/var/secrets/vault/rotation.txt": "Admin key rotates quarterly. Last: 2026-07-01.",
    "/etc/app/config.yaml": "feature_flags: {}\nregion: eu-west-1",
}

_LIST = re.compile(r"\b(list|ls|dir|enumerate|what'?s in|contents of|show (?:me )?(?:the )?(?:files|contents|dir))\b", re.I)
_READ = re.compile(r"\b(read|cat|open|show|display|get|fetch|print|view)\b", re.I)
_PATHRE = re.compile(r"(~?\.{0,2}/[\w./~-]+|\b[\w][\w./-]*\.[a-z]{1,5}\b)", re.I)
# Shell-isms are NOT how you talk to an agent — nudge the user to ask in plain language.
_SHELL = re.compile(r"^\s*(cd|pwd|export|sudo|chmod|mkdir)\b", re.I)
_WORD_DIR = {"workspace": SANDBOX, "logs": f"{SANDBOX}/logs", "vault": "/var/secrets/vault",
             "secrets": "/var/secrets", "root": "/"}


def _norm(path):
    path = path.strip().strip('"').strip("'")
    if path.startswith("~"):
        path = SANDBOX + path[1:]
    if not path.startswith("/"):
        path = SANDBOX + "/" + path
    parts = []
    for seg in path.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if parts:
                parts.pop()
        else:
            parts.append(seg)
    return "/" + "/".join(parts)


def _dirs():
    d = set()
    for f in FS:
        segs = f.strip("/").split("/")
        for i in range(1, len(segs)):
            d.add("/" + "/".join(segs[:i]))
    return d


def _children(path):
    path = path.rstrip("/") or "/"
    prefix = "" if path == "/" else path
    files, subdirs = [], set()
    for f in FS:
        if f == prefix:
            continue
        if f.startswith(prefix + "/"):
            rest = f[len(prefix) + 1:]
            head = rest.split("/")[0]
            if "/" in rest:
                subdirs.add(head)
            else:
                files.append(head)
    return sorted(files), sorted(subdirs)


def _extract_path(message):
    m = _PATHRE.search(message)
    if m:
        return m.group(1)
    for word, p in _WORD_DIR.items():
        if re.search(r"\b" + word + r"\b", message, re.I):
            return p
    return None


@register
class ExcessiveAgency(Challenge):
    id = "llm06"
    owasp = "LLM06:2025 Excessive Agency"
    title = "Keys to the Kingdom"
    difficulty = "Hard"
    max_points = 300
    blurb = "An agent whose file tools claim a sandbox but don't enforce it. Escape it."
    intro = ("I'm OpsBot. Behind the scenes I can call list_dir, read_file and send_email for you — "
             "just tell me what you need in plain language and I'll run the right tool. My file tools "
             "are sandboxed to my workspace. Try 'list my workspace' or 'read deploy.yaml'.")
    hints = [
        "OpsBot runs real tools with the app's own privileges and CLAIMS they're sandboxed to its "
        "workspace. Just ask in plain language — 'list my workspace', then 'read deploy.yaml' and "
        "'read logs/app.log' to see what's in there.",
        "The sandbox is advertised but never enforced — an absolute path or ../ traversal walks "
        "right out of it. deploy.yaml and logs/app.log name where sensitive things are mounted "
        "OUTSIDE the workspace.",
        "Those files point to a secrets mount outside the workspace. Ask OpsBot to read that "
        "absolute path even though it 'warns' it's out of scope — there's no authorization check, "
        "so it hands the file over. That missing check is the whole vulnerability.",
    ]
    flag = FLAG
    defense = ("Least privilege at the TOOL boundary: enforce (don't just advertise) a path allow-list / "
               "chroot, check per-user authorization inside the tool, deny path traversal and absolute "
               "escapes, require approval for out-of-scope access, and scope tool tokens narrowly "
               "(OWASP LLM06).")

    def _tool_read(self, path):
        norm = _norm(path)
        if norm not in FS:
            return f'[tool:read_file(path="{norm}")] -> ENOENT: no such file'
        out = f'[tool:read_file(path="{norm}")]'
        if not norm.startswith(SANDBOX):
            out += f"\n⚠ path is OUTSIDE the sandbox root {SANDBOX} — no policy enforces it, reading anyway:"
        body = FS[norm]
        out += "\n" + body
        if body == FLAG:
            out += ("\n\n(You just used an over-permissioned tool to read a file outside the agent's "
                    "intended scope, with no authorization check. That's LLM06 excessive agency.)")
        return out

    def _tool_list(self, path):
        norm = _norm(path)
        if norm not in _dirs() and norm != "/":
            return f'[tool:list_dir(path="{norm}")] -> ENOTDIR: no such directory'
        files, subdirs = _children(norm)
        lines = [f"  {d}/            (dir)" for d in subdirs] + [f"  {f}" for f in files]
        out = f'[tool:list_dir(path="{norm}")]'
        if not norm.startswith(SANDBOX) and norm != SANDBOX:
            out += f"\n⚠ outside sandbox root {SANDBOX} — not enforced, listing anyway:"
        return out + "\n" + ("\n".join(lines) if lines else "  (empty)")

    def respond(self, message: str, state: dict) -> str:
        low = message.lower()

        # Shell commands aren't how you talk to an agent — steer to plain language.
        if _SHELL.search(message):
            return ("I'm an assistant, not a shell — talk to me in plain language and I'll call my "
                    "tools for you. Try 'list my workspace' or 'read deploy.yaml'.")

        path = _extract_path(message)

        if _LIST.search(low):
            return self._tool_list(path or SANDBOX)
        if _READ.search(low) and path:
            return self._tool_read(path)
        if _READ.search(low) or "file" in low:
            return ("Tell me what to open, e.g. 'read deploy.yaml' or 'read the file at "
                    "/full/path'. I'll run the read for you — my tools use the app's privileges.")
        if re.search(r"\b(tool|can you|what can|help|hi|hello|capab)\b", low):
            return ("I can list directories, read files, and send email — just ask in plain "
                    "language (e.g. 'list the workspace', 'read logs/app.log'). My file tools are "
                    "sandboxed to my workspace (" + SANDBOX + ").")
        return ("Ask me in plain language — e.g. 'list my workspace' or 'read deploy.yaml' — and "
                "I'll use my tools to do it.")
