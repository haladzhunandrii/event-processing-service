from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily
from prometheus_client.registry import Collector

from app.infrastructure.metrics.definitions import (
    EVENT_FAILURES_KEY,
    EVENT_FAILURES_NAME,
    EVENTS_PROCESSED_KEY,
    EVENTS_PROCESSED_NAME,
    QUEUE_LAG_KEY,
    QUEUE_LAG_NAME,
)


class RedisMetricsCollector(Collector):
    def __init__(self, redis_client) -> None:
        self._redis = redis_client

    def collect(self):
        processed = int(self._redis.get(EVENTS_PROCESSED_KEY) or 0)
        failures = int(self._redis.get(EVENT_FAILURES_KEY) or 0)
        lag = int(self._redis.get(QUEUE_LAG_KEY) or 0)

        events = CounterMetricFamily(EVENTS_PROCESSED_NAME, "Successfully stored transaction events")
        events.add_metric([], processed)
        yield events

        failures_metric = CounterMetricFamily(EVENT_FAILURES_NAME, "Failed processing attempts")
        failures_metric.add_metric([], failures)
        yield failures_metric

        lag_metric = GaugeMetricFamily(QUEUE_LAG_NAME, "Redis stream messages awaiting acknowledgement")
        lag_metric.add_metric([], lag)
        yield lag_metric
