import json

from redis.exceptions import ConnectionError, TimeoutError

from src.infra.decorators import tenacity_retry_wrapper
from src.infra.external.redis_manager import RedisManager
from src.infra.logger import get_logger
from src.infra.settings import settings

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
    async def publish_event(self, event: dict, queue: str = settings.process_documents_channel) -> None:
        """Publish an event to the event bus."""
        try:
            client = await self.redis_manager.get_async_client()
            await client.publish(queue, json.dumps(event))
            logger.info(f"Event published to {queue}: {event}")
        except (ConnectionError, TimeoutError) as e:
            logger.exception(f"Failed to publish event to {queue}: {e}")
            raise
