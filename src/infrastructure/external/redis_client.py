import redis.asyncio as redis
from redis import Redis

# from redis.asyncio.client import Redis
from rq import Queue

from src.infrastructure.common.logger import get_logger
from src.infrastructure.config.settings import settings

logger = get_logger()


class RedisClient:
    """Asynchronous Redis client for the application."""

    def __init__(
        self,
        decode_responses: bool = True,
    ) -> None:
        """Initialize Redis client using settings configuration.

        Args:
            decode_responses: Whether to decode byte responses to strings.
        """
        try:
            if settings.redis_url:
                self.async_client = redis.from_url(settings.redis_url, decode_responses=decode_responses)
                logger.info(f"Initialized Redis client using URL: {settings.redis_url}")
            else:
                # Fallback to direct connection parameters
                self.async_client = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    username=settings.redis_user if settings.redis_user != "default" else None,
                    password=settings.redis_password
                    if settings.redis_password and settings.redis_password.lower() != "none"
                    else None,
                    decode_responses=decode_responses,
                )
                logger.info(f"Initialized Redis client for host: {settings.redis_host}, port: {settings.redis_port}")
            self.sync_client = Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                username=settings.redis_user if settings.redis_user != "default" else None,
                password=settings.redis_password
                if settings.redis_password and settings.redis_password.lower() != "none"
                else None,
                decode_responses=False,
            )
            self.processing_queue = Queue(
                settings.redis_queue_name,
                connection=self.sync_client,
                default_timeout=settings.processing_queue_timeout,
            )
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise

    def get_queue(self) -> Queue:
        """Get the RQ queue for processing jobs."""
        return self.processing_queue
