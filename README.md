# Transaction Event Service

A small Python/FastAPI service for asynchronous transaction ingestion. It is sized for the requested roughly 100 events/second with short bursts around 1,000/sec.

## Run locally

```bash
docker compose up --build
```

Submit an event (the worker normally processes it immediately):

```bash
curl -X POST http://localhost:8000/events -H "Content-Type: application/json" -d '{"id":"tx-1","user_id":"u-42","amount":"100.00","currency":"EUR","timestamp":"2026-08-31T12:00:00Z"}'
curl http://localhost:8000/users/u-42/summary
curl "http://localhost:8000/users/u-42/transactions?from=2026-08-01T00:00:00Z&to=2026-09-01T00:00:00Z"
curl http://localhost:8000/metrics
```

The local rate table seeds USD=1, EUR=1.08, and UAH=0.024 on first start. It intentionally models rate lookup as a database dependency, so a database outage naturally exercises retry behavior. In a real deployment, a separately operated rate-ingestion process would maintain this table.

Run unit tests without Docker after installing dependencies:

```bash
pytest -q
```

## Design choices

**Queue:** Redis Streams with AOF persistence and a consumer group. It keeps the HTTP path quick and durable, supports pending-message recovery, and is very simple to run in Compose. PostgreSQL is the source of truth for processed transactions.

**Delivery semantics: at-least-once.** The worker writes the transaction in a DB transaction, then acknowledges the stream message. It never acknowledges a failed message. If it crashes after commit but before acknowledgement, Redis redelivers it; the transaction id is PostgreSQL's primary key, so that duplicate has no effect. This is the practical trade-off instead of distributed exactly-once transactions across Redis and PostgreSQL.

Failures of PostgreSQL or the rate query leave the message pending and retry with exponential backoff (2s through 60s). A worker restart retains both the pending message and retry state. A replacement worker can claim stale pending messages by configuring Redis consumer recovery; for this compact single-worker deployment, Compose restarts the same worker and it resumes its own pending entries.

**One trade-off:** Redis Streams is an operationally lightweight queue but does not offer Kafka's partitioned replay and long-term retention. At 10× load, I would move to Kafka (partitioned by `user_id`), run multiple consumer replicas, use managed/replicated Redis or remove it entirely, and maintain rates with a provider-backed cache plus observability/alerts.

The `/metrics` endpoint exposes Prometheus counters for processed events and failures plus a pending-message lag gauge.
