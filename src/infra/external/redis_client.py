from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis

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
        try:
            return SyncRedis.from_url(
                settings.redis_url,
                username=settings.redis_user if settings.redis_user != "default" else None,
                password=settings.redis_password if settings.redis_password != "none" else None,
                decode_responses=decode_responses,
            )
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}", exc_info=True)
            raise
