from prometheus_client import Counter, Gauge

EVENTS_PROCESSED = Counter("events_processed_total", "Successfully stored transaction events")
EVENT_FAILURES = Counter("event_processing_failures_total", "Failed processing attempts")
QUEUE_LAG = Gauge("queue_lag", "Redis stream messages awaiting acknowledgement")
