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
def test_event_flow_end_to_end():
    event_id = f"integration-{int(time.time())}"
    with httpx.Client(base_url=BASE_URL, timeout=5.0) as client:
        response = client.post(
            "/events",
            json={
                "id": event_id,
                "user_id": "integration-user",
                "amount": "50.00",
                "currency": "EUR",
                "timestamp": "2026-08-31T12:00:00Z",
            },
        )
        assert response.status_code == 202

        summary = None
        for _ in range(20):
            summary = client.get("/users/integration-user/summary").json()
            if summary["transaction_count"] >= 1:
                break
            time.sleep(0.5)

        assert summary is not None
        assert summary["transaction_count"] >= 1
        assert summary["total_usd"] == "54.0000"
