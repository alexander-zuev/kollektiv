import json

from redis.asyncio.client import PubSub
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
        self.pubsub: PubSub | None = None

    @classmethod
    async def create_async(cls, redis_manager: RedisManager) -> "EventPublisher":
        """Creates an instance of EventPublisher and connects to pub/sub."""
        instance = cls(redis_manager)
        await instance.connect_pubsub()
        return instance

    @tenacity_retry_wrapper(exceptions=(ConnectionError, TimeoutError))
    async def connect_pubsub(self) -> None:
        """Connect to pub/sub."""
        redis_client = await self.redis_manager.get_async_client()
        if self.pubsub is None:
            try:
                self.pubsub = redis_client.pubsub()
                logger.info("✓ Connected to pub/sub successfully")
            except (ConnectionError, TimeoutError) as e:
                logger.exception(f"Failed to connect to pub/sub: {e}")
                raise

    async def get_pubsub_async(self) -> PubSub:
        """Get the pubsub client."""
        await self.connect_pubsub()
        return self.pubsub

    @tenacity_retry_wrapper(exceptions=(ConnectionError, TimeoutError))
    async def publish_event(self, event: dict, queue: str = settings.process_documents_channel) -> None:
        """Publish an event to the event bus."""
        try:
            await self.pubsub.publish(queue, json.dumps(event))
            logger.info(f"Event published to {queue}: {event}")
        except (ConnectionError, TimeoutError) as e:
            logger.exception(f"Failed to publish event to {queue}: {e}")
            raise
