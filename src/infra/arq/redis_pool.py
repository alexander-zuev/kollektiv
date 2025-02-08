from __future__ import annotations

from arq import ArqRedis, create_pool

from src.infra.arq.arq_settings import ArqSettings, get_arq_settings
from src.infra.logger import get_logger
from src.infra.settings import get_settings

settings = get_settings()
arq_settings = get_arq_settings()
logger = get_logger()


class RedisPool:
    """Manages ARQ Redis connection pool with consistent serialization."""

    def __init__(self, arq_settings: ArqSettings = arq_settings) -> None:
        self.arq_settings = arq_settings
        self._pool: ArqRedis | None = None

    @property
    def is_connected(self) -> bool:
        """Check if the Redis connection pool is connected."""
        return self._pool is not None

    async def initialize_pool(self) -> None:
        """Initialize the Redis connection pool, if not already initialized."""
        if self.is_connected:
            return
        try:
            logger.debug("Initializing Redis connection pool...")
            self._pool = await create_pool(
                settings_=self.arq_settings.redis_settings,
                job_serializer=self.arq_settings.job_serializer,
                job_deserializer=self.arq_settings.job_deserializer,
                retry=self.arq_settings.connection_retries,
            )
            logger.info("✓ Redis connection pool initialized successfully")
        except Exception as e:
            logger.exception(f"Failed to initialize Redis connection pool: {e}", exc_info=True)
            raise

    @classmethod
    async def create_redis_pool(cls) -> ArqRedis:
        """Create a RedisPool instance, initialize the pool and return it."""
        instance = cls()

        # Initialize .pool if not set
        await instance.initialize_pool()
        if not instance._pool:
            raise RuntimeError("Redis connection pool not initialized")
        return instance._pool

    async def get_pool(self) -> ArqRedis:
        """Get the connected pool instance or reconnect if necessary."""
        await self.initialize_pool()
        if not self._pool:
            raise RuntimeError("Redis connection pool not initialized")
        return self._pool
