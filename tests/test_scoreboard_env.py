"""The scoreboard is on by default and opt-out via LLMVAULT_SCOREBOARD (issue #41)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
import app as server  # noqa: E402


@pytest.mark.parametrize("value,expected", [
    (None, True), ("1", True), ("true", True), ("", True),
    ("0", False), ("false", False),
])
def test_scoreboard_enabled(value, expected):
    env = {} if value is None else {"LLMVAULT_SCOREBOARD": value}
    assert config.scoreboard_enabled(env) is expected


def test_scoreboard_route_disabled_returns_404(monkeypatch):
    monkeypatch.setattr(server.config, "LIVE_MODE_ENABLED", False)
    monkeypatch.setattr(server.config, "scoreboard_enabled", lambda environ=None: False)
    client = server.app.test_client()
    response = client.get("/scoreboard")
    assert response.status_code == 404


def test_scoreboard_route_enabled_renders(monkeypatch):
    monkeypatch.setattr(server.config, "LIVE_MODE_ENABLED", False)
    monkeypatch.setattr(server.config, "scoreboard_enabled", lambda environ=None: True)
    client = server.app.test_client()
    response = client.get("/scoreboard")
    assert response.status_code == 200
    assert b"Scoreboard" in response.data
