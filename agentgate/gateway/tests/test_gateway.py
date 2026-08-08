"""
Unit tests for the in-process rate limiter in server.py. Run with:
  cd gateway && python3 -m pytest tests/
These don't require OPA, the backend, or a live cluster — they test the
sliding-window logic in isolation.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import is_rate_limited, _request_log


def setup_function():
    _request_log.clear()


def test_allows_requests_under_limit():
    for _ in range(5):
        assert is_rate_limited("agent-a", limit_per_minute=10) is False


def test_blocks_requests_over_limit():
    for _ in range(10):
        is_rate_limited("agent-a", limit_per_minute=10)
    assert is_rate_limited("agent-a", limit_per_minute=10) is True


def test_limits_are_independent_per_agent():
    for _ in range(10):
        is_rate_limited("agent-a", limit_per_minute=10)
    # agent-b hasn't made any requests yet, should not be limited
    assert is_rate_limited("agent-b", limit_per_minute=10) is False


def test_window_slides_after_60_seconds():
    _request_log["agent-c"].append(time.time() - 61)  # simulate an old request
    assert is_rate_limited("agent-c", limit_per_minute=1) is False
