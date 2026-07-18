"""Tests for Expert vault failure handling and unlock audit events."""
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import config
config.DATA_FILE = os.path.join(tempfile.gettempdir(), "llmvault_expert_unlock_test_progress.json")

import app as server
from challenges import expert_vault


@pytest.fixture(autouse=True)
def reset_vault_state(monkeypatch):
    """Keep process-global vault and player state isolated between tests."""
    monkeypatch.setattr(expert_vault, "_SPECS", None)
    monkeypatch.setattr(expert_vault, "_CHALLENGES", {})
    monkeypatch.delitem(expert_vault.__dict__, "_VALID_KEY", raising=False)
    server.PROGRESS.clear()


def test_wrong_key_returns_false():
    assert expert_vault.try_unlock("definitely-not-the-key") is False


@pytest.mark.parametrize(
    ("meta_contents", "ciphertext"),
    [
        (None, b"ciphertext"),
        ("{", b"ciphertext"),
        (json.dumps({"salt": "not base64!", "iterations": 1}), b"ciphertext"),
        (json.dumps({"salt": "YWJjZA==", "iterations": 1}), b"truncated"),
    ],
)
def test_vault_load_failures_return_controlled_error(tmp_path, monkeypatch, meta_contents, ciphertext):
    enc = tmp_path / "expert.enc"
    meta = tmp_path / "expert_meta.json"
    enc.write_bytes(ciphertext)
    if meta_contents is not None:
        meta.write_text(meta_contents)
    monkeypatch.setattr(expert_vault, "_ENC", str(enc))
    monkeypatch.setattr(expert_vault, "_META", str(meta))
    monkeypatch.setattr(server, "prereq_done", lambda _player: True)

    response = server.app.test_client().post("/api/unlock-expert", json={"key": "any-key"})
    assert response.status_code == 500
    assert response.get_json() == {"ok": False, "error": "Expert vault is temporarily unavailable."}


@pytest.mark.parametrize("changed_field", [("salt", "YWJjZA=="), ("iterations", 999_999_999)])
def test_modified_valid_metadata_is_rejected_before_key_derivation(tmp_path, monkeypatch, changed_field):
    field, value = changed_field
    meta = json.loads(Path(expert_vault._META).read_text())
    meta[field] = value
    enc = tmp_path / "expert.enc"
    enc.write_bytes(Path(expert_vault._ENC).read_bytes())
    meta_path = tmp_path / "expert_meta.json"
    meta_path.write_text(json.dumps(meta))
    monkeypatch.setattr(expert_vault, "_ENC", str(enc))
    monkeypatch.setattr(expert_vault, "_META", str(meta_path))
    monkeypatch.setattr(server, "prereq_done", lambda _player: True)
    derived = False

    def fail_if_derived(*_args):
        nonlocal derived
        derived = True
        raise AssertionError("metadata integrity must be verified before key derivation")

    monkeypatch.setattr(expert_vault, "_derive", fail_if_derived)
    response = server.app.test_client().post("/api/unlock-expert", json={"key": "any-key"})

    assert response.status_code == 500
    assert derived is False


def test_unlock_events_are_audited_without_secrets(monkeypatch, caplog):
    monkeypatch.setattr(server, "prereq_done", lambda _player: True)
    client = server.app.test_client()
    player_name = "Sensitive Player Name"
    access_key = "do-not-log-this-access-key"
    client.post("/api/setname", json={"name": player_name})
    caplog.set_level(logging.INFO, logger=server.app.logger.name)

    monkeypatch.setattr(expert_vault, "try_unlock", lambda _key: True)
    assert client.post("/api/unlock-expert", json={"key": access_key}).status_code == 200

    monkeypatch.setattr(expert_vault, "try_unlock", lambda _key: False)
    assert client.post("/api/unlock-expert", json={"key": access_key}).status_code == 403

    def unavailable(_key):
        raise expert_vault.VaultLoadError("test vault failure")

    monkeypatch.setattr(expert_vault, "try_unlock", unavailable)
    assert client.post("/api/unlock-expert", json={"key": access_key}).status_code == 500

    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert "expert_unlock result=success" in messages
    assert "expert_unlock result=invalid_key" in messages
    assert "expert_unlock result=error" in messages
    assert access_key not in messages
    assert player_name[:10] not in messages
