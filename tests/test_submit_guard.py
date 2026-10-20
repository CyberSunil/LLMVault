"""Brute-force protection tests for /api/submit (GitHub issue #43).

Policy under test:
  - SUBMIT_MAX_ATTEMPTS (5) consecutive wrong submissions trigger a 30-second
    cooldown on a per-player, per-challenge basis.
  - While locked: any submission returns HTTP 429 with retry_after > 0,
    even if the correct flag is sent.
  - After the cooldown expires the attempt counter resets and submissions work
    normally again.
  - A correct submission always clears the failed-attempt state.
  - Failures on one challenge do NOT affect other challenges.

Time is monkeypatched so no test actually sleeps.
"""
import os
import sys
import tempfile

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import config

config.DATA_FILE = os.path.join(
    tempfile.gettempdir(), "llmvault_submit_guard_test_progress.json"
)

import app as server
from challenges import core_labs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WRONG_FLAG = "LLMVAULT{this-is-definitely-wrong}"
MAX = config.SUBMIT_MAX_ATTEMPTS       # 5
COOLDOWN = config.SUBMIT_LOCKOUT_SECONDS  # 30


def _client_with_name(name: str):
    """Return a fresh test client that has set a player name."""
    cl = server.app.test_client()
    cl.post("/api/setname", json={"name": name})
    return cl


def _first_lab():
    """Return the first core lab (always accessible to a fresh player)."""
    return core_labs()[0]


def _second_lab():
    """Return the second core lab (used for isolation tests)."""
    return core_labs()[1]


def _submit(cl, cid: str, flag: str):
    return cl.post("/api/submit", json={"cid": cid, "flag": flag})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_progress():
    """Wipe in-memory progress between every test."""
    server.PROGRESS.clear()
    yield
    server.PROGRESS.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestNormalIncorrectAttempts:
    """Attempts 1-4 should behave normally (HTTP 200, correct=False)."""

    def test_first_wrong_attempt_returns_200(self):
        cl = _client_with_name("guard-t1")
        c = _first_lab()
        r = _submit(cl, c.id, WRONG_FLAG)
        assert r.status_code == 200
        assert r.get_json()["correct"] is False

    def test_failed_attempts_counter_increments(self):
        cl = _client_with_name("guard-t2")
        c = _first_lab()
        for _ in range(3):
            _submit(cl, c.id, WRONG_FLAG)
        player = list(server.PROGRESS.values())[-1]
        guard = player.get("submit_guard", {}).get(c.id, {})
        assert guard.get("failed_attempts") == 3

    def test_four_wrong_attempts_still_200(self):
        cl = _client_with_name("guard-t3")
        c = _first_lab()
        for i in range(MAX - 1):  # 4 attempts
            r = _submit(cl, c.id, WRONG_FLAG)
            assert r.status_code == 200, f"attempt {i + 1} should be 200"
            assert r.get_json()["correct"] is False


class TestThresholdActivatesLockout:
    """The MAX-th consecutive wrong attempt triggers HTTP 429 and starts the cooldown."""

    def test_fifth_wrong_attempt_returns_429(self):
        cl = _client_with_name("guard-t4")
        c = _first_lab()
        for _ in range(MAX - 1):
            _submit(cl, c.id, WRONG_FLAG)
        r = _submit(cl, c.id, WRONG_FLAG)  # 5th
        assert r.status_code == 429

    def test_429_response_contains_error_and_retry_after(self):
        cl = _client_with_name("guard-t5")
        c = _first_lab()
        for _ in range(MAX):
            r = _submit(cl, c.id, WRONG_FLAG)
        body = r.get_json()
        assert "error" in body
        assert "retry_after" in body
        assert body["retry_after"] > 0

    def test_retry_after_on_threshold_equals_cooldown(self):
        cl = _client_with_name("guard-t6")
        c = _first_lab()
        for _ in range(MAX):
            r = _submit(cl, c.id, WRONG_FLAG)
        assert r.get_json()["retry_after"] == COOLDOWN


class TestLockedState:
    """While the cooldown is active all submissions return 429."""

    def test_request_during_lockout_returns_429(self, monkeypatch):
        cl = _client_with_name("guard-t7")
        c = _first_lab()
        # Trigger lockout
        for _ in range(MAX):
            _submit(cl, c.id, WRONG_FLAG)
        # Advance time by only 10 seconds (still locked)
        base = server.time.time()
        monkeypatch.setattr(server.time, "time", lambda: base + 10)
        r = _submit(cl, c.id, WRONG_FLAG)
        assert r.status_code == 429

    def test_retry_after_reflects_remaining_cooldown(self, monkeypatch):
        cl = _client_with_name("guard-t8")
        c = _first_lab()
        for _ in range(MAX):
            _submit(cl, c.id, WRONG_FLAG)
        # 10 seconds have passed -> ~20 s remaining
        base = server.time.time()
        monkeypatch.setattr(server.time, "time", lambda: base + 10)
        r = _submit(cl, c.id, WRONG_FLAG)
        body = r.get_json()
        assert r.status_code == 429
        # math.ceil rounds up: with 20 s remaining, retry_after == 20
        assert 0 < body["retry_after"] <= COOLDOWN - 10

    def test_correct_flag_during_lockout_returns_429_not_200(self, monkeypatch):
        """Even the correct flag must NOT be validated while locked."""
        cl = _client_with_name("guard-t9")
        c = _first_lab()
        for _ in range(MAX):
            _submit(cl, c.id, WRONG_FLAG)
        # Still within cooldown window
        base = server.time.time()
        monkeypatch.setattr(server.time, "time", lambda: base + 5)
        r = _submit(cl, c.id, c.flag)
        assert r.status_code == 429
        # Challenge must NOT be marked solved
        player = list(server.PROGRESS.values())[-1]
        assert c.id not in player.get("solved", {})


class TestCooldownExpiry:
    """After the cooldown expires, submissions work again."""

    def test_submission_works_after_cooldown(self, monkeypatch):
        cl = _client_with_name("guard-t10")
        c = _first_lab()
        for _ in range(MAX):
            _submit(cl, c.id, WRONG_FLAG)
        # Jump past the cooldown
        base = server.time.time()
        monkeypatch.setattr(server.time, "time", lambda: base + COOLDOWN + 1)
        r = _submit(cl, c.id, WRONG_FLAG)
        assert r.status_code == 200

    def test_attempt_counter_resets_after_cooldown(self, monkeypatch):
        cl = _client_with_name("guard-t11")
        c = _first_lab()
        for _ in range(MAX):
            _submit(cl, c.id, WRONG_FLAG)
        base = server.time.time()
        monkeypatch.setattr(server.time, "time", lambda: base + COOLDOWN + 1)
        # One wrong attempt after expiry - should be 200 and counter == 1
        r = _submit(cl, c.id, WRONG_FLAG)
        assert r.status_code == 200
        player = list(server.PROGRESS.values())[-1]
        guard = player["submit_guard"][c.id]
        assert guard["failed_attempts"] == 1


class TestCorrectSubmissionClearsGuard:
    """A correct submission resets guard state and preserves solve behaviour."""

    def test_correct_submission_resets_counter(self):
        cl = _client_with_name("guard-t12")
        c = _first_lab()
        for _ in range(MAX - 1):
            _submit(cl, c.id, WRONG_FLAG)
        r = _submit(cl, c.id, c.flag)
        assert r.status_code == 200
        assert r.get_json()["correct"] is True
        player = list(server.PROGRESS.values())[-1]
        guard = player["submit_guard"][c.id]
        assert guard["failed_attempts"] == 0
        assert guard["locked_until"] == 0.0

    def test_correct_submission_marks_challenge_solved(self):
        cl = _client_with_name("guard-t13")
        c = _first_lab()
        r = _submit(cl, c.id, c.flag)
        assert r.status_code == 200
        body = r.get_json()
        assert body["correct"] is True
        assert body["solved"] is True
        assert body["score"] > 0

    def test_correct_submission_after_partial_failures(self):
        """Correct flag must work after fewer-than-max wrong attempts."""
        cl = _client_with_name("guard-t14")
        c = _first_lab()
        for _ in range(2):
            _submit(cl, c.id, WRONG_FLAG)
        r = _submit(cl, c.id, c.flag)
        assert r.status_code == 200
        assert r.get_json()["correct"] is True


class TestCrossChallengeIsolation:
    """Failures on one challenge must NOT affect a different challenge."""

    def test_lockout_on_one_challenge_does_not_affect_another(self):
        cl = _client_with_name("guard-t15")
        c1 = _first_lab()
        c2 = _second_lab()
        # Lock out c1
        for _ in range(MAX):
            _submit(cl, c1.id, WRONG_FLAG)
        assert _submit(cl, c1.id, WRONG_FLAG).status_code == 429
        # c2 should still accept submissions normally
        r = _submit(cl, c2.id, WRONG_FLAG)
        assert r.status_code == 200

    def test_attempts_accumulate_independently_per_challenge(self):
        cl = _client_with_name("guard-t16")
        c1 = _first_lab()
        c2 = _second_lab()
        for _ in range(2):
            _submit(cl, c1.id, WRONG_FLAG)
        for _ in range(3):
            _submit(cl, c2.id, WRONG_FLAG)
        player = list(server.PROGRESS.values())[-1]
        assert player["submit_guard"][c1.id]["failed_attempts"] == 2
        assert player["submit_guard"][c2.id]["failed_attempts"] == 3


class TestExistingSolveBehaviourUnchanged:
    """Ensure the original solve / scoring logic is intact."""

    def test_solving_awards_points(self):
        cl = _client_with_name("guard-t17")
        c = _first_lab()
        r = _submit(cl, c.id, c.flag)
        body = r.get_json()
        assert body["correct"] is True
        assert body["score"] == c.max_points

    def test_solving_already_solved_does_not_double_count(self):
        cl = _client_with_name("guard-t18")
        c = _first_lab()
        _submit(cl, c.id, c.flag)
        r = _submit(cl, c.id, c.flag)
        assert r.get_json()["score"] == c.max_points  # still just max_points, not doubled

    def test_wrong_submission_returns_correct_false(self):
        cl = _client_with_name("guard-t19")
        c = _first_lab()
        r = _submit(cl, c.id, WRONG_FLAG)
        assert r.status_code == 200
        assert r.get_json()["correct"] is False
