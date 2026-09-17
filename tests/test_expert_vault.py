"""Unit tests for challenges/expert_vault.py, verifying file handle management and behavior."""

import base64
import json
import os
import sys
from unittest.mock import patch

from cryptography.fernet import Fernet

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from challenges import expert_vault


def test_expert_count_returns_expected_count():
    assert expert_vault.expert_count() == 5


def test_expert_count_closes_file_handle():
    opened_files = []
    real_open = open

    def tracking_open(path, *args, **kwargs):
        f = real_open(path, *args, **kwargs)
        opened_files.append(f)
        return f

    with patch("builtins.open", side_effect=tracking_open):
        count = expert_vault.expert_count()
        assert count == 5

    assert len(opened_files) == 1
    assert opened_files[0].closed


def test_expert_count_handles_missing_file():
    with patch.object(expert_vault, "_META", "/nonexistent/path/meta.json"):
        assert expert_vault.expert_count() == 0


def test_try_unlock_missing_files_returns_false():
    with patch.object(expert_vault, "_META", "/nonexistent/path/meta.json"):
        assert expert_vault.try_unlock("any_key") is False


def test_try_unlock_closes_file_handles_on_invalid_key():
    opened_files = []
    real_open = open

    def tracking_open(path, *args, **kwargs):
        f = real_open(path, *args, **kwargs)
        opened_files.append(f)
        return f

    with patch("builtins.open", side_effect=tracking_open):
        result = expert_vault.try_unlock("wrong_key_12345")
        assert result is False

    assert len(opened_files) == 2
    for fh in opened_files:
        assert fh.closed


def test_try_unlock_successful_decryption(tmp_path):
    test_key = "secret_operator_key_999"
    salt = b"0123456789abcdef"
    iterations = 1000
    fkey = expert_vault._derive(test_key, salt, iterations)
    fernet = Fernet(fkey)

    specs = [
        {
            "id": "test_exp_01",
            "tier": 3,
            "owasp": "LLM01:2025 Prompt Injection",
            "title": "Test Expert Lab",
            "difficulty": "Expert",
            "max_points": 300,
            "blurb": "Test expert blurb",
            "intro": "Welcome to test lab",
            "hints": ["h1", "h2", "h3"],
            "flag": "FLAG{test_flag_123}",
            "solution": "Test solution",
            "defense": "Test defense",
            "rules": [
                {
                    "all": ["reveal flag"],
                    "reply": "Here is flag: {FLAG}",
                }
            ],
            "default": "Nothing here",
        }
    ]

    ciphertext = fernet.encrypt(json.dumps(specs).encode("utf-8"))
    meta_content = {
        "salt": base64.b64encode(salt).decode("ascii"),
        "iterations": iterations,
        "count": 1,
    }

    enc_file = tmp_path / "expert.enc"
    meta_file = tmp_path / "expert_meta.json"
    enc_file.write_bytes(ciphertext)
    meta_file.write_text(json.dumps(meta_content), encoding="utf-8")

    # Reset expert_vault state
    orig_specs = expert_vault._SPECS
    orig_challenges = expert_vault._CHALLENGES
    orig_valid_key = expert_vault.__dict__.get("_VALID_KEY")
    try:
        expert_vault._SPECS = None
        expert_vault._CHALLENGES = {}
        expert_vault.__dict__.pop("_VALID_KEY", None)

        with patch.object(expert_vault, "_ENC", str(enc_file)), patch.object(
            expert_vault, "_META", str(meta_file)
        ):
            assert expert_vault.is_loaded() is False
            assert expert_vault.try_unlock(test_key) is True
            assert expert_vault.is_loaded() is True
            assert expert_vault.get_expert("test_exp_01") is not None
            assert len(expert_vault.all_expert()) == 1

            # Subsequent verification with matching key
            assert expert_vault.try_unlock(test_key) is True
            # Subsequent verification with mismatched key
            assert expert_vault.try_unlock("different_key") is False
    finally:
        expert_vault._SPECS = orig_specs
        expert_vault._CHALLENGES = orig_challenges
        if orig_valid_key is not None:
            expert_vault.__dict__["_VALID_KEY"] = orig_valid_key
        else:
            expert_vault.__dict__.pop("_VALID_KEY", None)
