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


class VaultLoadError(RuntimeError):
    """The encrypted vault could not be loaded because of a server-side fault."""


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
    """Attempt to decrypt the vault with the supplied key. True on success."""
    global _SPECS, _CHALLENGES
    if _SPECS is not None:
        # already decrypted this process; verify the supplied key still matches
        return _verify(access_key)
    if not (os.path.exists(_ENC) and os.path.exists(_META)):
        raise VaultLoadError("expert vault files are missing")
    try:
        with open(_META) as meta_file:
            meta = json.load(meta_file)
        salt = base64.b64decode(meta["salt"], validate=True)
        fkey = _derive(access_key.strip(), salt, meta["iterations"])
        with open(_ENC, "rb") as encrypted_file:
            encrypted = encrypted_file.read()
        plain = Fernet(fkey).decrypt(encrypted)
        specs = json.loads(plain)
        challenges = {s["id"]: DeclarativeChallenge(s) for s in specs}
    except InvalidToken:
        return False
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise VaultLoadError("expert vault could not be loaded") from exc
    _SPECS = specs
    _CHALLENGES = challenges
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
