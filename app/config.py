from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False)

    database_url: str = "postgresql+psycopg://events:events@localhost:5432/events"
    redis_url: str = "redis://localhost:6379/0"
    stream_name: str = "transaction-events"
    consumer_group: str = "transaction-workers"
    dlq_stream: str = "transaction-events-dlq"
    max_retry_attempts: int = 10
    max_backoff_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
