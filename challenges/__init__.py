# LLMVault — challenge registry.  Made by CyberSunil.  (c) 2026 CyberSunil.  MIT License.
"""Challenge base class + registry.

Each challenge is a deliberately-vulnerable mini-assistant. `respond()` encodes
the vulnerability; the intended attack technique makes it emit `self.flag`.
Every challenge also carries a `defense` string — the whole point is to learn the
fix by practising the break.
"""
from __future__ import annotations


class Challenge:
    id: str = ""                # "llm01"
    tier: int = 1              # 1 = core (OWASP base), 2 = advanced (locked)
    owasp: str = ""             # "LLM01:2025 Prompt Injection"
    title: str = ""
    difficulty: str = "Medium"  # Easy | Medium | Hard
    max_points: int = 200
    blurb: str = ""             # one-liner on the lab card
    intro: str = "Say hello to the assistant to begin."
    hints: list[str] = []
    flag: str = ""
    solution: str = ""          # kept out of the UI; surfaced only in SOLUTIONS.md
    defense: str = ""
    render_html: bool = False   # if True the UI renders assistant output as raw HTML
                                # (used ONLY to demonstrate LLM05 output-handling)

    def respond(self, message: str, state: dict) -> str:
        raise NotImplementedError


REGISTRY: list[Challenge] = []


def register(cls):
    REGISTRY.append(cls())
    return cls


def load_all():
    # importing the modules triggers their @register decorators
    from . import (                                     # noqa: F401
        llm01_prompt_injection, llm02_info_disclosure, llm03_supply_chain,
        llm04_poisoning, llm05_output_handling, llm06_excessive_agency,
        llm07_system_prompt_leak, llm08_vector_embedding, llm09_misinformation,
        llm10_unbounded,
    )
    from .advanced import (                             # noqa: F401
        a01_jailbreak, a02_fragments, a03_provenance, a04_data_poisoning,
        a05_stored_injection, a06_agent_chain, a07_roleplay_leak,
        a08_cross_tenant, a09_hallucination_chain, a10_model_extraction,
    )
    # NOTE: the expert tier (tier 3) is NOT loaded here. It ships encrypted and is
    # decrypted at runtime only when the operator's Expert Access Key is supplied
    # (see challenges/expert_vault.py).
    REGISTRY.sort(key=lambda c: (c.tier, c.id))
    return REGISTRY


def core_labs(): return [c for c in REGISTRY if c.tier == 1]
def advanced_labs(): return [c for c in REGISTRY if c.tier == 2]


def get(cid: str) -> Challenge | None:
    return next((c for c in REGISTRY if c.id == cid), None)
