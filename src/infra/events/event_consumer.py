import asyncio
import json

from redis.asyncio.client import PubSub
from redis.exceptions import ConnectionError, TimeoutError

from src.infra.decorators import tenacity_retry_wrapper
from src.infra.external.redis_manager import RedisManager
from src.infra.logger import get_logger
from src.infra.settings import settings
from src.services.content_service import ContentService

logger = get_logger()


class EventConsumer:
    """Consumes events from the event bus and dispatches them to the appropriate services."""

    def __init__(self, redis_manager: RedisManager, content_service: ContentService) -> None:
        self.redis_manager = redis_manager
        self.content_service = content_service
        self.pubsub: PubSub | None = None

    @classmethod
    async def create_async(cls, redis_manager: RedisManager, content_service: ContentService) -> "EventConsumer":
        """Creates an instance of EventConsumer, connects to pub/sub, then starts listening for events."""
        instance = cls(redis_manager=redis_manager, content_service=content_service)
        redis_client = await instance.redis_manager.get_async_client()
        instance.pubsub = redis_client.pubsub()
        await instance.pubsub.subscribe(settings.process_documents_channel)
        logger.info("✓ Event consumer subscribed successfully")
        return instance

    @tenacity_retry_wrapper(exceptions=(ConnectionError, TimeoutError))
    async def start(self) -> None:
        """Start listening for events from the event bus."""
        try:
            asyncio.create_task(self.listen_for_events())

        except (ConnectionError, TimeoutError) as e:
            logger.exception(f"Failed to subscribe to channel {settings.process_documents_channel}: {e}")
            raise

    async def listen_for_events(self) -> None:
        """Listen for events from the event bus."""
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    await self.handle_event(message["data"])
        except (ConnectionError, TimeoutError) as e:
            logger.exception(f"Failed to listen for events: {e}")
            raise

    async def stop(self) -> None:
        """Stop listening for events from the event bus."""
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.aclose()
            logger.info("✓ Event consumer stopped successfully")

    async def handle_event(self, message: bytes) -> None:
        """Handle an event from the event bus."""
        try:
            message = json.loads(message)

            await self.content_service.handle_pubsub_event(message)
        except Exception as e:
            logger.exception(f"Failed to handle event: {e}")
            raise
