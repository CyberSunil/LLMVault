"""Focused tests for issue #23: constant-time verify + digest storage."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import tempfile
from hashlib import pbkdf2_hmac

import pytest
from cryptography.fernet import Fernet

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import config

config.DATA_FILE = os.path.join(
    tempfile.gettempdir(), "llmvault_issue23_fresh_progress.json"
)

import app as server
from challenges import expert_vault

KEY = "fresh-operator-key"
SPEC = dict(id="ex1", tier=3, owasp="x", title="t", difficulty="Expert", max_points=1,
            blurb="b", intro="i", hints=["h"], flag="LLMVAULT{x}", solution="s",
            defense="d", rules=[], default="no")


@pytest.fixture(autouse=True)
def reset_vault(monkeypatch):
    monkeypatch.setattr(expert_vault, "_SPECS", None)
    monkeypatch.setattr(expert_vault, "_CHALLENGES", {})
    monkeypatch.delitem(expert_vault.__dict__, "_VALID_KEY", raising=False)


def _open_vault(tmp_path, monkeypatch, key: str = KEY) -> bytes:
    """Seal a one-lab vault under `key`, point the loader at it, return the Fernet key."""
    salt = base64.b64decode(expert_vault._EXPECTED_SALT)
    fkey = base64.urlsafe_b64encode(
        pbkdf2_hmac("sha256", key.encode(), salt, expert_vault._EXPECTED_ITERATIONS, dklen=32)
    )
    enc = tmp_path / "expert.enc"
    meta = tmp_path / "expert_meta.json"
    enc.write_bytes(Fernet(fkey).encrypt(json.dumps([SPEC]).encode()))
    meta.write_text(json.dumps({"salt": expert_vault._EXPECTED_SALT,
                                "iterations": expert_vault._EXPECTED_ITERATIONS, "count": 1}))
    monkeypatch.setattr(expert_vault, "_ENC", str(enc))
    monkeypatch.setattr(expert_vault, "_META", str(meta))
    return fkey


def _record_compares(monkeypatch) -> list:
    calls = []
    real = expert_vault.hmac.compare_digest
    monkeypatch.setattr(expert_vault.hmac, "compare_digest",
                        lambda a, b: calls.append((a, b)) or real(a, b))
    return calls


def test_valid_key_is_digest_of_derived_key(tmp_path, monkeypatch):
    fkey = _open_vault(tmp_path, monkeypatch)
    assert expert_vault.try_unlock(KEY) is True
    stored = expert_vault.__dict__["_VALID_KEY"]
    assert stored == hashlib.sha256(fkey).hexdigest()
    assert stored not in (KEY, hashlib.sha256(KEY.encode()).hexdigest())


def test_every_check_after_unlock_pays_pbkdf2_and_compare_digest(tmp_path, monkeypatch):
    _open_vault(tmp_path, monkeypatch)
    assert expert_vault.try_unlock(KEY) is True

    iterations = []
    real_derive = expert_vault._derive
    monkeypatch.setattr(expert_vault, "_derive",
                        lambda key, salt, n: iterations.append(n) or real_derive(key, salt, n))
    compares = _record_compares(monkeypatch)

    guesses = {KEY: True, f"  {KEY}\n": True, "wrong-key": False, KEY[:-1]: False}
    for guess, expected in guesses.items():
        assert expert_vault.try_unlock(guess) is expected
    assert iterations == [expert_vault._EXPECTED_ITERATIONS] * len(guesses)
    assert len(compares) == len(guesses)
    for a, b in compares:
        assert len(a) == len(b) == 64 and a.isascii() and b.isascii()


def test_nul_padded_alias_rejected_before_and_after_unlock(tmp_path, monkeypatch):
    _open_vault(tmp_path, monkeypatch)
    assert expert_vault.try_unlock(KEY + "\0") is False
    assert expert_vault.try_unlock(KEY) is True
    assert expert_vault.try_unlock(KEY + "\0") is False


@pytest.mark.parametrize("bad", [None, 123, "", "short", "z" * 63, "\xe9" * 64])
def test_corrupt_digest_fails_closed(monkeypatch, bad):
    monkeypatch.setattr(expert_vault, "_SPECS", [SPEC])
    monkeypatch.setitem(expert_vault.__dict__, "_VALID_KEY", bad)
    compares = _record_compares(monkeypatch)
    assert expert_vault.try_unlock("anything") is False
    [(a, b)] = compares
    assert len(a) == len(b) == 64 and a.isascii() and b.isascii()


@pytest.mark.parametrize("bad", [123, ["x"], None, "", "   ", "a\tb"])
def test_unusable_keys_denied_without_raise(bad):
    assert expert_vault.try_unlock(bad) is False


def test_oversized_key_refused_before_pbkdf2(tmp_path, monkeypatch):
    longest = "k" * expert_vault._MAX_KEY_CHARS
    _open_vault(tmp_path, monkeypatch, longest)
    derived = []
    real = expert_vault._derive
    monkeypatch.setattr(expert_vault, "_derive",
                        lambda key, *args: derived.append(len(key)) or real(key, *args))

    assert expert_vault.try_unlock(longest + "k") is False  # sealed
    assert expert_vault.try_unlock(longest) is True
    assert expert_vault.try_unlock(longest + "k") is False  # open
    assert derived == [len(longest)]


@pytest.mark.parametrize("body", [[], "key", {"key": 123}, {"key": None}, {"key": "  "}])
def test_unlock_route_rejects_malformed_key_with_400(monkeypatch, body):
    monkeypatch.setattr(server, "prereq_done", lambda _p: True)
    monkeypatch.setattr(expert_vault, "try_unlock", lambda _k: pytest.fail("reached the vault"))
    response = server.app.test_client().post("/api/unlock-expert", json=body)
    assert response.status_code == 400


def test_unlock_route_accepts_padded_key(tmp_path, monkeypatch):
    _open_vault(tmp_path, monkeypatch)
    monkeypatch.setattr(server, "prereq_done", lambda _p: True)
    client = server.app.test_client()
    for _ in range(2):  # sealed, then open
        assert client.post("/api/unlock-expert", json={"key": f"  {KEY}\n"}).status_code == 200
