from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import ConnectionError, TimeoutError

from src.infra.decorators import tenacity_retry_wrapper
from src.infra.logger import get_logger
from src.infra.settings import settings

logger = get_logger()


class RedisManager:
    """Redis client that handles both sync and async connections."""

    def __init__(self, decode_responses: bool = True) -> None:
        """Initialize Redis clients using settings configuration.

        Args:
            decode_responses: Whether to decode byte responses to strings.
                           Note: RQ requires decode_responses=False
        """
        self._decode_responses = decode_responses
        self._sync_client: SyncRedis | None = None
        self._async_client: AsyncRedis | None = None

    def _create_sync_client(self, decode_responses: bool) -> SyncRedis:
        """Create sync Redis client."""
        client = SyncRedis.from_url(
            url=settings.redis_url,
            decode_responses=decode_responses,
        )
        return client

    def _create_async_client(self, decode_responses: bool) -> AsyncRedis:
        """Create async Redis client."""
        client = AsyncRedis.from_url(
            url=settings.redis_url,
            decode_responses=decode_responses,
        )
        return client

    @tenacity_retry_wrapper(exceptions=(ConnectionError, TimeoutError))
    def _connect_sync(self) -> None:
        """Connect to the sync redis client and handle connection errors."""
        if self._sync_client is None:
            try:
                client = self._create_sync_client(decode_responses=self._decode_responses)
                client.ping()
                self._sync_client = client
                logger.info("✓ Initialized sync Redis client successfully")
            except (ConnectionError, TimeoutError) as e:
                logger.exception(f"Failed to initialize sync Redis client: {e}")
                raise

    @tenacity_retry_wrapper(exceptions=(ConnectionError, TimeoutError))
    async def _connect_async(self) -> None:
        """Connect to the async redis client and handle connection errors."""
        if self._async_client is None:
            try:
                client = self._create_async_client(decode_responses=self._decode_responses)
                await client.ping()
                self._async_client = client
                logger.info("✓ Initialized async Redis client successfully")
            except (ConnectionError, TimeoutError) as e:
                logger.exception(f"Failed to initialize async Redis client: {e}")
                raise

    @classmethod
    def create(cls, decode_responses: bool = True) -> "RedisManager":
        """Creates a new sync redis client"""
        instance = cls(decode_responses=decode_responses)
        instance._connect_sync()
        return instance

    @classmethod
    async def create_async(cls, decode_responses: bool = True) -> "RedisManager":
        """Creates a new async redis client"""
        instance = cls(decode_responses=decode_responses)
        await instance._connect_async()
        return instance

    def get_sync_client(self) -> SyncRedis:
        """Get the sync redis client"""
        self._connect_sync()
        if self._sync_client is None:
            raise RuntimeError("Sync Redis client not initialized")
        return self._sync_client

    async def get_async_client(self) -> AsyncRedis:
        """Get the async redis client"""
        await self._connect_async()
        if self._async_client is None:
            raise RuntimeError("Async Redis client not initialized")
        return self._async_client
