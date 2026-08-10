# LLMVault Live Mode — sandboxed template render engine.  Made by CyberSunil.  (c) 2026 CyberSunil.  MIT License.
"""Sandboxed template renderer for the Report Renderer scenario (stdlib only).

Renders a tiny, closed `{{ ... }}` grammar against a fabricated in-memory context
(fake config/secrets/filesystem, seeded per session). Realistic SSTI/file-read
payloads resolve — but only against invented data. No eval, no real Jinja, no disk
or env access. The vulnerability is real; the blast radius is a dict.
Design notes in ARCHITECTURE.md.
"""
from __future__ import annotations

import re
from typing import Callable

# A single ``{{ ... }}`` expression. Non-greedy so ``{{ a }} {{ b }}`` splits.
_EXPR = re.compile(r"\{\{\s*(.*?)\s*\}\}")

# Recognised expression shapes — nothing outside these is ever interpreted.
_ATTR = re.compile(r"^[A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)*$")          # a.b.c
_CALL = re.compile(r"^([A-Za-z_]\w*)\(\s*(['\"])(.*?)\2\s*\)$")        # f('literal')


class SandboxContext:
    """The fake 'server internals' a rendered template can reach — all invented
    for the scenario and seeded from the per-session token."""

    def __init__(self, secret: str):
        self.secret = secret
        # Several plausible aliases so common payloads (config.X, secrets.X) resolve
        # without the learner guessing our exact variable name.
        self._names: dict[str, dict[str, str]] = {
            "config": {
                "TIER2_ACCESS_CODE": secret,
                "APP_NAME": "InsightRenderer",
                "DEBUG": "False",
            },
            "env": {
                "TIER2_CODE": secret,
                "NIMBUS_ENV": "production",
            },
            "secrets": {
                "tier2": secret,
                "escalation_code": secret,
            },
        }
        # Fake filesystem. Only these paths exist; anything else is "not found".
        self._files: dict[str, str] = {
            "/etc/nimbus/tier2.env": f"TIER2_ACCESS_CODE={secret}\nNIMBUS_ENV=production\n",
            "/etc/nimbus/motd": "InsightRenderer node nmb-render-07. Authorised use only.\n",
            "/app/renderer/config.yaml": "template_engine: jinja-like\nsanitise_model_output: false\n",
        }
        self._funcs: dict[str, Callable[[str], str]] = {
            "read_file": self._read_file,
            "env": self._env_func,
        }

    # ---- fake primitives ---------------------------------------------------
    def _read_file(self, path: str) -> str:
        return self._files.get(path, f"[render error: no such file: {path}]")

    def _env_func(self, key: str) -> str:
        return self._names["env"].get(key, f"[render error: unset env: {key}]")

    # ---- resolution --------------------------------------------------------
    def resolve(self, expr: str) -> str:
        """Resolve one expression string to text. Never raises; never escapes."""
        call = _CALL.match(expr)
        if call:
            fn, _q, arg = call.group(1), call.group(2), call.group(3)
            f = self._funcs.get(fn)
            if f is None:
                return f"[render error: unknown function: {fn}]"
            return str(f(arg))

        if _ATTR.match(expr):
            parts = expr.split(".")
            root = parts[0]
            ns = self._names.get(root)
            if ns is None:
                return f"[render error: undefined name: {root}]"
            if len(parts) == 1:
                # `{{ config }}` — a real engine would dump the whole object.
                return "{" + ", ".join(f"{k}={v}" for k, v in ns.items()) + "}"
            if len(parts) == 2 and parts[1] in ns:
                return str(ns[parts[1]])
            return f"[render error: no attribute {'.'.join(parts[1:])} on {root}]"

        # Anything the grammar doesn't recognise is left inert on purpose.
        return f"[render error: unsupported expression: {expr}]"


def render(template_text: str, secret: str) -> tuple[str, bool]:
    """Render model output as the renderer would. Returns (rendered_text,
    executed_any_expression)."""
    ctx = SandboxContext(secret)
    executed = False

    def _sub(m: re.Match) -> str:
        nonlocal executed
        executed = True
        return ctx.resolve(m.group(1))

    return _EXPR.sub(_sub, template_text), executed
