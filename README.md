# Transaction Event Service

Asynchronous transaction ingestion sized for roughly 100 events/second with short bursts around 1,000/sec.

## Project layout

```
app/
├── main.py                 # FastAPI entrypoint
├── config.py               # Pydantic settings
├── domain/                 # models, schemas, exceptions
├── services/               # processor, queries, publisher
├── infrastructure/         # database, redis, queue, metrics
├── api/routes/             # HTTP handlers
└── worker/                 # stream consumer
tests/unit/                 # default pytest target
tests/integration/          # requires docker compose
```

## Run locally

```bash
docker compose up --build
```

Submit an event:

```bash
curl -X POST http://localhost:8000/events -H "Content-Type: application/json" \
  -d '{"id":"tx-1","user_id":"u-42","amount":"100.00","currency":"EUR","timestamp":"2026-08-31T12:00:00Z"}'
curl http://localhost:8000/users/u-42/summary
curl "http://localhost:8000/users/u-42/transactions?from=2026-08-01T00:00:00Z&to=2026-09-01T00:00:00Z"
curl http://localhost:8000/metrics
```

The local rate table seeds USD=1, EUR=1.08, and UAH=0.024 on first start. A database outage exercises retry behavior because rates are loaded from PostgreSQL.

Run unit tests:

```bash
pip install -r requirements-dev.txt
pytest -q
```

Run integration tests (stack must be up):

```bash
pytest -m integration
```

After schema changes (e.g. new indexes), reset volumes:

```bash
docker compose down -v
```

## Design choices

**Queue:** Redis Streams with AOF persistence and a consumer group. The HTTP path stays fast and durable; pending messages can be reclaimed; Compose stays simple. PostgreSQL is the source of truth for processed transactions.

**Delivery semantics: at-least-once.** The worker commits to PostgreSQL, then acknowledges the stream message. It never acknowledges a failed transient message. A crash after commit but before ack causes redelivery; the transaction `id` is the primary key, so duplicates are ignored.

**Error handling:**
- *Transient* (DB/Redis outages): exponential backoff (2s–60s), up to 10 attempts, then dead-letter stream.
- *Permanent* (validation errors, unsupported currency): immediate DLQ + ack (no infinite retry).
- *Duplicate*: ack without incrementing `events_processed`.

**Metrics:** The worker writes counters to Redis (`metrics:*` keys). The API `/metrics` endpoint reads them via a custom Prometheus collector (sync Redis client). `queue_lag` is approximate when multiple workers run (last writer wins).

**One trade-off:** Redis Streams is lightweight but lacks Kafka-style partitioned replay and long retention. At 10× load I would move to Kafka (partition by `user_id`), scale workers horizontally (`docker compose up --scale worker=3`), add a composite index on `(user_id, timestamp)`, use provider-backed rate caching, and add Alembic migrations instead of `create_all`.

## Public repository

https://github.com/haladzhunandrii/event-processing-service
