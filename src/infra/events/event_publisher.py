from redis.exceptions import ConnectionError, TimeoutError

from src.infra.decorators import tenacity_retry_wrapper
from src.infra.external.redis_manager import RedisManager
from src.infra.logger import get_logger

logger = get_logger()


class EventPublisher:
    """Responsible for publishing events to the event bus."""

    def __init__(self, redis_manager: RedisManager) -> None:
        self.redis_manager = redis_manager

    @classmethod
    async def create_async(cls, redis_manager: RedisManager) -> "EventPublisher":
        """Creates an instance of EventPublisher."""
        instance = cls(redis_manager)
        return instance

    @tenacity_retry_wrapper(exceptions=(ConnectionError, TimeoutError))
    async def publish_event(
        self,
        channel: str,
        message: dict,
    ) -> None:
        """
        Publish a message to the event bus.

        Args:
            channel: The channel to publish to
            message: The message to publish (will be JSON serialized)
        """
        try:
            client = await self.redis_manager.get_async_client()

            message = message.model_dump_json()
            logger.debug(f"Trying to save message type: {type(message)}")

            await client.publish(channel, message)
            logger.info(f"Event published to {channel}: {message}")
        except (ConnectionError, TimeoutError) as e:
            logger.exception(f"Failed to publish event to {channel}: {e}")
            raise
