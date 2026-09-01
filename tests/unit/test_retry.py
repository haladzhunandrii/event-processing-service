import asyncio
import time

import pytest

from app.infrastructure.queue.retry import compute_backoff, should_attempt


def test_compute_backoff_caps_at_max():
    assert compute_backoff(1) == 2
    assert compute_backoff(2) == 4
    assert compute_backoff(5) == 32
    assert compute_backoff(6) == 60
    assert compute_backoff(10) == 60


def test_should_attempt_respects_backoff(monkeypatch):
    class FakeRedis:
        async def hget(self, key, field):
            return "1000.0"

    fake_redis = FakeRedis()
    monkeypatch.setattr("app.infrastructure.queue.retry.time.time", lambda: 500.0)
    assert asyncio.run(should_attempt(fake_redis, "msg-1")) is False

    monkeypatch.setattr("app.infrastructure.queue.retry.time.time", lambda: 1500.0)
    assert asyncio.run(should_attempt(fake_redis, "msg-1")) is True
