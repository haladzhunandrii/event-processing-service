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
def test_metrics_exposes_processed_counter():
    event_id = f"metrics-{int(time.time())}"
    with httpx.Client(base_url=BASE_URL, timeout=5.0) as client:
        client.post(
            "/events",
            json={
                "id": event_id,
                "user_id": "metrics-user",
                "amount": "10.00",
                "currency": "USD",
                "timestamp": "2026-08-31T12:00:00Z",
            },
        )

        metrics_text = ""
        for _ in range(20):
            metrics_text = client.get("/metrics").text
            if "events_processed_total" in metrics_text:
                break
            time.sleep(0.5)

        assert "events_processed_total" in metrics_text
