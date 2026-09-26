"""Runtime loader for the encrypted expert tier.

Ships as ciphertext (expert.enc) + public KDF params (expert_meta.json). The
plaintext challenges/flags exist ONLY after a correct Expert Access Key is supplied
by the operator. Wrong key -> authenticated decryption fails -> no content.

Security model (Kerckhoffs): the code, salt, and ciphertext are all public; secrecy
rests entirely on the operator-held key. Reverse-engineering yields ciphertext only.
"""
from __future__ import annotations

import base64
import json
import os
import re
from hashlib import pbkdf2_hmac

from cryptography.fernet import Fernet, InvalidToken

from . import Challenge

_HERE = os.path.dirname(os.path.abspath(__file__))
_ENC = os.path.join(_HERE, "expert.enc")
_META = os.path.join(_HERE, "expert_meta.json")

_SPECS: list[dict] | None = None          # populated only after a valid unlock
_CHALLENGES: dict[str, "DeclarativeChallenge"] = {}

# Expected (pinned) KDF parameters. The public meta file must match these exactly;
# any deviation means the metadata was tampered with, and we reject it BEFORE deriving
# a key. This is the integrity gate the security tests require.
_EXPECTED_SALT = "EMKqrY702tO/UFN2yKJbvg=="
_EXPECTED_ITERATIONS = 200000


class VaultLoadError(Exception):
    """Raised when the vault files are missing, malformed, or fail integrity checks.

    Distinct from a wrong access key (which is a normal 'denied' outcome): this signals
    the vault itself can't be loaded, so the endpoint returns a controlled 500 instead
    of leaking a stack trace.
    """


class DeclarativeChallenge(Challenge):
    """A challenge whose vulnerable behaviour is a list of match-rules (from the vault)."""
    def __init__(self, spec: dict):
        super().__init__()
        self.id = spec["id"]; self.tier = spec["tier"]; self.owasp = spec["owasp"]
        self.title = spec["title"]; self.difficulty = spec["difficulty"]
        self.max_points = spec["max_points"]; self.blurb = spec["blurb"]
        self.intro = spec["intro"]; self.hints = spec["hints"]; self.flag = spec["flag"]
        self.solution = spec["solution"]; self.defense = spec["defense"]
        self._rules = spec["rules"]; self._default = spec["default"]

    def respond(self, message: str, state: dict) -> str:
        for rule in self._rules:
            if all(re.search(p, message, re.I) for p in rule.get("all", [])) and \
               all(state.get(f) for f in rule.get("requires", [])):
                for f in rule.get("sets", []):
                    state[f] = True
                return rule["reply"].replace("{FLAG}", self.flag)
        return self._default


def _derive(access_key: str, salt: bytes, iterations: int) -> bytes:
    dk = pbkdf2_hmac("sha256", access_key.encode(), salt, iterations, dklen=32)
    return base64.urlsafe_b64encode(dk)


def try_unlock(access_key: str) -> bool:
    """Attempt to decrypt the vault with the supplied key.

    Returns True on success, False on a wrong key. Raises VaultLoadError if the vault
    files are missing, malformed, or fail integrity checks (so the caller can return a
    controlled error rather than crashing).
    """
    global _SPECS, _CHALLENGES
    if _SPECS is not None:
        # already decrypted this process; verify the supplied key still matches
        return _verify(access_key)
    if not (os.path.exists(_ENC) and os.path.exists(_META)):
        raise VaultLoadError("vault files not present")

    # --- load + validate metadata (controlled errors, no stack traces) ---
    try:
        with open(_META) as fh:
            meta = json.load(fh)
    except (ValueError, OSError) as e:
        raise VaultLoadError("metadata unreadable or not valid JSON") from e
    if not isinstance(meta, dict) or "salt" not in meta or "iterations" not in meta:
        raise VaultLoadError("metadata missing required fields")

    # --- integrity gate: metadata must match the pinned KDF params BEFORE deriving ---
    if meta.get("salt") != _EXPECTED_SALT or meta.get("iterations") != _EXPECTED_ITERATIONS:
        raise VaultLoadError("metadata integrity check failed")

    try:
        salt = base64.b64decode(meta["salt"], validate=True)
    except (ValueError, Exception) as e:  # binascii.Error subclasses ValueError
        raise VaultLoadError("metadata salt is not valid base64") from e

    fkey = _derive(access_key.strip(), salt, meta["iterations"])

    # --- decrypt: wrong key OR corrupt ciphertext ---
    try:
        ciphertext = open(_ENC, "rb").read()
    except OSError as e:
        raise VaultLoadError("ciphertext unreadable") from e
    try:
        plain = Fernet(fkey).decrypt(ciphertext)
    except InvalidToken:
        return False  # wrong key -> normal denial
    except Exception as e:
        # truncated/garbage ciphertext that isn't even a valid Fernet token
        raise VaultLoadError("ciphertext malformed") from e

    try:
        _SPECS = json.loads(plain)
    except ValueError as e:
        raise VaultLoadError("decrypted payload is not valid JSON") from e
    _CHALLENGES = {s["id"]: DeclarativeChallenge(s) for s in _SPECS}
    globals()["_VALID_KEY"] = access_key.strip()
    return True


def _verify(access_key: str) -> bool:
    return access_key.strip() == globals().get("_VALID_KEY")


def is_loaded() -> bool:
    return _SPECS is not None


def expert_count() -> int:
    try:
        return json.load(open(_META)).get("count", 0)
    except Exception:
        return 0


def all_expert() -> list["DeclarativeChallenge"]:
    return sorted(_CHALLENGES.values(), key=lambda c: c.id) if _SPECS else []


def get_expert(cid: str):
    return _CHALLENGES.get(cid)
