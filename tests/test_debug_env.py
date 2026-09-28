"""Debug mode comes from LLMVAULT_DEBUG and must stay off unless opted in."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
import app as server  # noqa: E402


@pytest.mark.parametrize("value,expected", [(None, False), ("1", True), ("true", True), ("0", False)])
def test_debug_enabled(value, expected):
    env = {} if value is None else {"LLMVAULT_DEBUG": value}
    assert config.debug_enabled(env) is expected


@pytest.mark.parametrize("debug", [True, False])
def test_main_forwards_debug_to_app_run(monkeypatch, debug):
    monkeypatch.setattr(server.config, "LIVE_MODE_ENABLED", False)
    monkeypatch.setattr(server.config, "DEBUG", debug)
    captured = {}
    monkeypatch.setattr(server.app, "run", lambda **kw: captured.update(kw))
    server.main()
    assert captured["debug"] is debug
