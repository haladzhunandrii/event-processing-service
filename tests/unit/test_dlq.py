import asyncio

from app.infrastructure.queue.dlq import move_to_dlq


def test_move_to_dlq_writes_stream():
    class FakeRedis:
        async def xadd(self, stream, fields):
            return f"{stream}-1"

    message_id = asyncio.run(
        move_to_dlq(
            FakeRedis(),
            "orig-1",
            {
                "event": '{"id":"evt-bad","user_id":"u1","amount":"1","currency":"XXX","timestamp":"2026-01-01T00:00:00Z"}'
            },
            "unsupported currency",
        )
    )
    assert message_id == "transaction-events-dlq-1"
