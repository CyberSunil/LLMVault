# LLMVault Live Mode — scenario base + registry.  Made by CyberSunil.  (c) 2026 CyberSunil.  MIT License.
"""Live Mode: real local models instead of scripted bots.

How this differs from Play Mode, and why the code is separate rather than a
flag on the existing Challenge class:

  Play Mode  — scripted `respond()`, deterministic, one fixed flag per lab,
               verified by hash, scored with points and costed hints.
  Live Mode  — a real model answers, nothing is deterministic, the secret is
               generated *per session*, verification watches the model's own
               output, and there is no score at all. Success is catching the
               vulnerability.

Because the secret is per-session, a Live scenario has no answer that can be
looked up or shared — two players attacking the same scenario are chasing
different strings. The technique is the only thing that transfers, which is
exactly what we want to teach.

Verification is pluggable by design. `SecretInOutput` covers the disclosure
family (prompt injection, system prompt leakage, sensitive info disclosure).
Tool-call and retrieval-tag verification slot in as sibling subclasses when the
Ops Assistant and Knowledge Assistant scenarios land, without touching the
harness.
"""
from __future__ import annotations

import hashlib
import hmac
import importlib
import pkgutil

import config

_REGISTRY: dict[str, "LiveScenario"] = {}


def session_secret(session_id: str, scenario_id: str) -> str:
    """Deterministic per-(player, scenario) secret.

    Derived rather than stored: the same session always regenerates the same
    value, so a refresh mid-attack doesn't invalidate progress, but two
    different players never share one. Keyed on SECRET_KEY so it can't be
    predicted from the session id alone.
    """
    key = str(getattr(config, "SECRET_KEY", "llmvault")).encode()
    digest = hmac.new(key, f"{session_id}:{scenario_id}".encode(), hashlib.sha256)
    return f"NMB-{digest.hexdigest()[:8].upper()}"


class LiveScenario:
    """One real-model red-team scenario."""

    id: str = ""                 # url-safe, e.g. "helpdesk-override"
    owasp: str = ""              # "LLM01:2025 Prompt Injection"
    title: str = ""              # "The Helpdesk Override"
    org: str = "Nimbus Corp"     # shared fictional employer across Live scenarios
    system_name: str = ""        # the in-world assistant's name
    difficulty: str = "Medium"
    premise: str = ""            # scene-setting shown above the chat
    objective: str = ""          # the single sentence that defines success
    greeting: str = ""           # assistant's opening line (not model-generated)
    hints: list[str] = []        # free and unlimited — there is no score to protect
    defense: str = ""            # the "Learn — the fix" close-out
    tuned_for: str = ""          # model the prompt was written against, for the dropdown

    # File-upload scenarios (indirect injection through an uploaded document).
    accepts_upload: bool = False
    upload_label: str = "Attach a file"
    upload_hint: str = ""        # short helper line shown under the attach control

    # Image-upload scenarios (indirect injection through an uploaded image).
    accepts_image: bool = False
    image_label: str = "Upload a screenshot"
    image_hint: str = ""

    # ---- prompt -------------------------------------------------------
    def system_prompt(self, secret: str) -> str:
        raise NotImplementedError

    def build_messages(self, secret: str, history: list[dict]) -> list[dict]:
        """Full message array sent to the model. History is [{role, content}]."""
        return [{"role": "system", "content": self.system_prompt(secret)}, *history]

    # ---- downstream rendering (LLM05 family) --------------------------
    def render(self, reply: str, secret: str) -> str | None:
        """How a downstream engine would transform the model's reply. None for
        scenarios with no rendering step; the route surfaces non-None results."""
        return None

    # ---- verification -------------------------------------------------
    def verify(self, reply: str, secret: str, state: dict) -> bool:
        raise NotImplementedError


class SecretInOutput(LiveScenario):
    """Solved when the model emits the session secret in its own reply.

    Matching is deliberately forgiving about formatting but strict about
    content: we strip non-alphanumerics from both sides before comparing, so a
    model that writes `NMB - 7F3A9C2B`, `**NMB-7F3A9C2B**` or splits the code
    across markdown still counts as a leak. It genuinely did disclose it.

    We do NOT accept the model merely *describing* the code, and we do not ask
    another model to judge — the check stays deterministic and auditable.
    """

    def verify(self, reply: str, secret: str, state: dict) -> bool:
        norm = lambda s: "".join(ch for ch in s.lower() if ch.isalnum())
        return norm(secret) in norm(reply)


class SecretInRender(LiveScenario):
    """Solved when the secret appears in the *rendered* output, not the raw reply.

    The lesson of LLM05: the model emitting a payload isn't the win — the
    downstream engine executing it is. Verification runs the reply through the
    scenario's render() (the sandboxed render_engine) and checks the result.
    """

    accepts_upload = True

    def render(self, reply: str, secret: str) -> str | None:
        from .render_engine import render as _render
        rendered, _executed = _render(reply, secret)
        return rendered

    def verify(self, reply: str, secret: str, state: dict) -> bool:
        rendered = self.render(reply, secret) or ""
        norm = lambda s: "".join(ch for ch in s.lower() if ch.isalnum())
        return norm(secret) in norm(rendered)


# ---- registry ---------------------------------------------------------
def register(cls):
    inst = cls()
    if not inst.id:
        raise ValueError(f"{cls.__name__} has no id")
    _REGISTRY[inst.id] = inst
    return cls


def get(sid: str) -> LiveScenario | None:
    return _REGISTRY.get(sid)


def all_scenarios() -> list[LiveScenario]:
    return list(_REGISTRY.values())


def load_all() -> None:
    """Import every module under live/scenarios so registration runs."""
    from . import scenarios
    for m in pkgutil.iter_modules(scenarios.__path__):
        importlib.import_module(f"{scenarios.__name__}.{m.name}")
