import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://events:events@localhost:5432/events")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STREAM = "transaction-events"
GROUP = "transaction-workers"
