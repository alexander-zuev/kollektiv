from collections.abc import Callable
from functools import lru_cache
from typing import Any
from uuid import UUID

import msgpack
from arq.connections import RedisSettings
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from src.infra.logger import get_logger
from src.infra.settings import get_settings

settings = get_settings()
logger = get_logger()


class ArqSettings(BaseSettings):
    """Centralized for the ARQ worker and connection pool."""

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

    def custom_serializer(self, obj: Any) -> bytes:
        """Serialize objects to bytes.

        Handles:
        - Pydantic BaseModel -> {"__pydantic__": class_name, "data": dict}
        - UUID -> {"__uuid__": str}
        - Lists and dicts containing above types (recursive)
        - All other types handled by msgpack
        """

    def _serialize(obj: Any) -> Any:
        if isinstance(obj, BaseModel):
            return {"__pydantic__": obj.__class__.__name__, "data": obj.model_dump(mode="json")}
        elif isinstance(obj, UUID):
            return {"__uuid__": str(obj)}
        elif isinstance(obj, (list, tuple)):
            return [_serialize(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: _serialize(value) for key, value in obj.items()}
        return obj

        return msgpack.packb(_serialize(obj))

    def custom_deserializer(self, data: bytes) -> Any:
        """Deserialize bytes back to objects.

        Handles:
        - {"__pydantic__": class_name, "data": dict} -> Pydantic BaseModel
        - {"__uuid__": str} -> UUID
        - Lists and dicts containing above types (recursive)
        - All other types handled by msgpack
        """

        def _deserialize(obj: Any) -> Any:
            if isinstance(obj, dict):
                model_name = obj.get("__pydantic__")
                uuid_str = obj.get("__uuid__")

                if model_name:
                    # Need to get actual class from model_name
                    return obj["data"].model_validate(obj["data"])
                elif uuid_str:
                    return UUID(uuid_str)
                return {key: _deserialize(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [_deserialize(item) for item in obj]
            return obj

        return _deserialize(msgpack.unpackb(data, raw=False))

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
            self._job_serializer = msgpack.packb
        return self._job_serializer

    @property
    def job_deserializer(self) -> Callable[[bytes], Any]:
        """Get the deserializer for the ARQ worker and redis pool."""
        if self._job_deserializer is None:
            self._job_deserializer = lambda b: msgpack.unpackb(_deserialize(b), raw=False)
        return self._job_deserializer


def initialize_arq_settings() -> ArqSettings:
    """Initialize the ARQ settings."""
    return ArqSettings()


arq_settings = initialize_arq_settings()


@lru_cache
def get_arq_settings() -> ArqSettings:
    """Get the cached ARQ settings."""
    return arq_settings
