import os
import time

import httpx
import pytest

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def _service_available() -> bool:
    try:
        httpx.get(f"{BASE_URL}/health", timeout=1.0)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.integration


@pytest.mark.skipif(not _service_available(), reason="docker compose stack is not running")
def test_invalid_currency_lands_in_dlq():
    event_id = f"dlq-{int(time.time())}"
    with httpx.Client(base_url=BASE_URL, timeout=5.0) as client:
        response = client.post(
            "/events",
            json={
                "id": event_id,
                "user_id": "dlq-user",
                "amount": "10.00",
                "currency": "XXX",
                "timestamp": "2026-08-31T12:00:00Z",
            },
        )
        assert response.status_code == 202

        summary = {"transaction_count": 0}
        for _ in range(20):
            summary = client.get("/users/dlq-user/summary").json()
            if summary["transaction_count"] > 0:
                break
            time.sleep(0.5)

        assert summary["transaction_count"] == 0
