from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import ConnectionError, TimeoutError

from src.infra.decorators import tenacity_retry_wrapper
from src.infra.logger import get_logger
from src.infra.settings import settings

logger = get_logger()


class RedisClient:
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

        try:
            # Initialize both clients using the same connection logic
            self.async_client = self._create_async_client(decode_responses)
            self.sync_client = self._create_sync_client(decode_responses=False)  # RQ needs this false

            logger.info("✓ Initialized Redis client successfully")
        except redis.ConnectionError as e:
            logger.error(f"Failed to initialize Redis client: {e}", exc_info=True)
            raise

    def _create_async_client(self, decode_responses: bool) -> AsyncRedis:
        """Create async Redis client."""
        try:
            return AsyncRedis.from_url(
                settings.redis_url,
                username=settings.redis_user if settings.redis_user != "default" else None,
                password=settings.redis_password if settings.redis_password != "none" else None,
                decode_responses=decode_responses,
            )
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}", exc_info=True)
            raise

    def _create_sync_client(self, decode_responses: bool) -> SyncRedis:
        """Create sync Redis client."""
        return SyncRedis.from_url(
            settings.redis_url,
            username=settings.redis_user if settings.redis_user != "default" else None,
            password=settings.redis_password if settings.redis_password != "none" else None,
            decode_responses=decode_responses,
        )

    @tenacity_retry_wrapper(exceptions=(ConnectionError, TimeoutError))
    def _connect_sync(self) -> None:
        """Connect to the sync redis client and handle connection errors."""
        if self._sync_client is None:
            try:
                self._sync_client = self._create_sync_client(decode_responses=self._decode_responses)
                logger.info("✓ Initialized sync Redis client successfully")
            except ConnectionError as e:
                logger.exception(f"Failed to initialize sync Redis client: {e}")
                raise

    @classmethod
    def create_sync_client(cls) -> "SyncRedis":
        """Creates a new sync redis client"""
        instance = cls()
        instance._connect_sync()
        return instance._sync_client

    def get_sync_client(self) -> SyncRedis:
        """Get the sync redis client"""
        self._connect_sync()
        return self._sync_client
