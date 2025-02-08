from pydantic import BaseModel
from redis.exceptions import ConnectionError, TimeoutError

from src.infra.decorators import tenacity_retry_wrapper
from src.infra.external.redis_manager import RedisManager
from src.infra.logger import get_logger

logger = get_logger()


class EventPublisher:
    """Responsible for publishing events to the event bus."""

    def __init__(self, redis_manager: RedisManager) -> None:
        self.redis_manager = redis_manager

    async def publish(self, channel: str, message: str) -> None:
        """Simple wrapper around publish_event."""
        # get the client
        client = await self.redis_manager.get_async_client()
        # publish the message
        await client.publish(channel, message)
        logger.info(f"Event published to {channel}: {message}")

    @classmethod
    async def create_async(cls, redis_manager: RedisManager) -> "EventPublisher":
        """Creates an instance of EventPublisher."""
        instance = cls(redis_manager)
        return instance

    @tenacity_retry_wrapper(exceptions=(ConnectionError, TimeoutError))
    async def publish_event(
        self,
        channel: str,
        message: BaseModel,
    ) -> None:
        """
        Publish a message to the event bus.

        Args:
            channel: The channel to publish to
            message: The message to publish (will be JSON serialized)
        """
        try:
            await self.publish(channel=channel, message=message.model_dump_json())
        except (ConnectionError, TimeoutError) as e:
            logger.exception(f"Failed to publish event to {channel}: {e}")
            raise
