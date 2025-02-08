from collections.abc import Callable
from functools import lru_cache
from typing import Any

from arq.connections import RedisSettings
from pydantic import Field
from pydantic_settings import BaseSettings

# Import custom serializer functions from our serializer module
from src.infra.arq.serializer import deserialize, serialize
from src.infra.logger import get_logger
from src.infra.settings import get_settings

settings = get_settings()
logger = get_logger()


class ArqSettings(BaseSettings):
    """Centralized settings for the ARQ worker and connection pool."""

    # Cache for properties
    _redis_settings: RedisSettings | None = None
    _job_serializer: Callable[[Any], bytes] | None = None
    _job_deserializer: Callable[[bytes], Any] | None = None

    # Redis pool settings
    redis_host: str = settings.redis_host
    redis_port: int = settings.redis_port
    redis_user: str | None = settings.redis_user
    redis_password: str | None = settings.redis_password
    connection_retries: int = Field(5, description="Number of connection retries to redis connection pool")

    # Worker settings
    job_retries: int = Field(3, description="Number of default job retries, decreased from 5 to 3")
    health_check_interval: int = Field(60, description="Health check interval")
    max_jobs: int = Field(1000, description="Maximum number of jobs in the queue")

    @property
    def redis_settings(self) -> RedisSettings:
        """Get the Redis settings."""
        if self._redis_settings is None:
            self._redis_settings = RedisSettings(
                host=self.redis_host,
                port=self.redis_port,
                username=self.redis_user,
                password=self.redis_password,
            )
        return self._redis_settings

    @property
    def job_serializer(self) -> Callable[[Any], bytes]:
        """Get the serializer for the ARQ worker and redis pool."""
        if self._job_serializer is None:
            self._job_serializer = serialize
        return self._job_serializer

    @property
    def job_deserializer(self) -> Callable[[bytes], Any]:
        """Get the deserializer for the ARQ worker and redis pool."""
        if self._job_deserializer is None:
            self._job_deserializer = deserialize
        return self._job_deserializer


def initialize_arq_settings() -> ArqSettings:
    """Initialize the ARQ settings."""
    return ArqSettings()


arq_settings = initialize_arq_settings()


@lru_cache
def get_arq_settings() -> ArqSettings:
    """Get the cached ARQ settings."""
    return arq_settings
