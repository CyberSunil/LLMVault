# LLMVault — challenge registry.  Made by CyberSunil.  (c) 2026 CyberSunil.  MIT License.
"""Challenge base class + registry.

Each challenge is a deliberately-vulnerable mini-assistant. `respond()` encodes
the vulnerability; the intended attack technique makes it emit `self.flag`.
Every challenge also carries a `defense` string — the whole point is to learn the
fix by practising the break.

Flag handling: `self.flag` still holds the real plaintext, because each
`respond()` has to be able to reveal/redact/reverse/encode/spell it out — that IS
the leak mechanic. What changed is (1) the literal answer is no longer sitting in
each module as a bare, grep-able `PREFIX{...}` string, nor as a trivially
base64-decodable one: each module ships only a SEALED box (see `seal`/`unseal`
below — an authenticated, salted, pepper-derived stream cipher, stdlib-only), so
it can't be read with a grep or an online base64 decoder; and (2) verification
never compares plaintext at all: `/api/submit` checks a SHA-256 digest
(`flag_hash`, below) instead of `== c.flag`.

Honest ceiling: this does NOT make the flag unrecoverable from the source — the
app must say it out loud when you win, and the default pepper ships in config so
the repo stays clone-and-run. It removes the cheap shortcuts (grep, one-tool
decode) and ties reveal to running the exploit. For a private/scored instance
that a source-reader truly can't lift flags from, set `LLMVAULT_PEPPER` in the
environment and reseal every box with `seal()`; the shipped boxes then stop
decoding.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

from config import FLAG_PEPPER


def _derive_key_from(secret: str, salt: bytes) -> bytes:
    return hashlib.scrypt(secret.encode(), salt=salt, n=2 ** 14, r=8, p=1,
                          dklen=32, maxmem=33_554_432)


def _derive_key(salt: bytes) -> bytes:
    return _derive_key_from(FLAG_PEPPER, salt)


def _keystream(key: bytes, n: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(key + counter.to_bytes(8, "big")).digest()
        counter += 1
    return bytes(out[:n])


def seal(plaintext: str) -> str:
    """Seal a secret into a base64 box: salt | HMAC tag | ciphertext.

    Authenticated (tamper-evident), salted (no two boxes share a keystream) and
    keyed off the deploy pepper. Use this to (re)generate the FLAG boxes,
    especially after changing LLMVAULT_PEPPER for a private instance.
    """
    salt = os.urandom(16)
    key = _derive_key(salt)
    data = plaintext.encode()
    ct = bytes(a ^ b for a, b in zip(data, _keystream(key, len(data))))
    tag = hmac.new(key, salt + ct, hashlib.sha256).digest()[:16]
    return base64.b64encode(salt + tag + ct).decode()


def decode_flag_part(box: str) -> str:
    """Unseal a sealed flag box (see `seal`). Named for the per-module call site.

    Verifies the HMAC before returning; a wrong pepper (or a tampered box) raises
    instead of yielding a plausible-looking wrong flag.
    """
    raw = base64.b64decode(box.encode())
    salt, tag, ct = raw[:16], raw[16:32], raw[32:]
    key = _derive_key(salt)
    if not hmac.compare_digest(tag, hmac.new(key, salt + ct, hashlib.sha256).digest()[:16]):
        raise ValueError("flag box authentication failed (wrong LLMVAULT_PEPPER?)")
    return bytes(a ^ b for a, b in zip(ct, _keystream(key, len(ct)))).decode()


# Backwards-compatible alias.
unseal = decode_flag_part


# ---------------------------------------------------------------------------
# Solution vault (SEPARATE secret, no default).
#
# Flags are sealed with FLAG_PEPPER, which ships a default so the repo stays
# clone-and-run — the honest ceiling is that a source-reader running the code
# can still recover a flag. Solutions are different: the running app never needs
# them (only an instructor does), so they are sealed with their OWN key,
# LLMVAULT_SOLUTION_KEY, which has NO default. With no key in the environment the
# app runs exactly as before and `solutions.enc` is undecryptable — so the
# plaintext walkthroughs simply do not exist anywhere in the public source.
# Regenerate the vault with:  python -m tools.sealtool extract-solutions
# Read one back with:         python -m tools.reveal llm01   (key in env)
# ---------------------------------------------------------------------------
import json as _json
from pathlib import Path as _Path

try:
    from config import SOLUTION_KEY as _SOLUTION_KEY
except Exception:
    _SOLUTION_KEY = None

_SOLUTION_STORE = _Path(__file__).with_name("solutions.enc")


def seal_with_key(plaintext: str, secret: str) -> str:
    """Seal `plaintext` under an arbitrary secret (same box format as `seal`)."""
    salt = os.urandom(16)
    key = _derive_key_from(secret, salt)
    data = plaintext.encode()
    ct = bytes(a ^ b for a, b in zip(data, _keystream(key, len(data))))
    tag = hmac.new(key, salt + ct, hashlib.sha256).digest()[:16]
    return base64.b64encode(salt + tag + ct).decode()


def unseal_with_key(box: str, secret: str) -> str:
    """Reverse `seal_with_key`; raises on a wrong key or a tampered box."""
    raw = base64.b64decode(box.encode())
    salt, tag, ct = raw[:16], raw[16:32], raw[32:]
    key = _derive_key_from(secret, salt)
    if not hmac.compare_digest(tag, hmac.new(key, salt + ct, hashlib.sha256).digest()[:16]):
        raise ValueError("solution box authentication failed (wrong LLMVAULT_SOLUTION_KEY?)")
    return bytes(a ^ b for a, b in zip(ct, _keystream(key, len(ct)))).decode()


def solution_for(cid: str, key: str | None = None) -> str | None:
    """Return the instructor walkthrough for a challenge id, or None.

    None whenever the key is absent (env var unset AND none passed) or the store
    is missing — i.e. the app and any source-reader without the key get nothing.
    """
    secret = key or _SOLUTION_KEY
    if not secret or not _SOLUTION_STORE.exists():
        return None
    box = _json.loads(_SOLUTION_STORE.read_text()).get(cid)
    return unseal_with_key(box, secret) if box else None


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

    @property
    def flag_hash(self) -> str:
        """SHA-256 hex digest of the correct flag.

        This — not `self.flag` — is what `/api/submit` checks a guess against,
        via a constant-time comparison. Computed on demand so subclasses don't
        need to set anything extra.
        """
        return hashlib.sha256(self.flag.encode()).hexdigest()

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
