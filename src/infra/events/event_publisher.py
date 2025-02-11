from typing import Any
from uuid import UUID

from pydantic import BaseModel
from redis.exceptions import ConnectionError, TimeoutError

from src.infra.decorators import tenacity_retry_wrapper
from src.infra.external.redis_manager import RedisManager
from src.infra.logger import get_logger
from src.models.content_models import ContentProcessingEvent, SourceStage
from src.models.pubsub_models import EventType, KollektivEvent

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

    @classmethod
    def create_event(
        cls,
        stage: SourceStage,
        source_id: UUID,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> KollektivEvent:
        """Creates a type of KollektivEvent.

        Args:
            source_id: ID of the source being processed
            stage: Enum of Sources tages
            error: Optional error message if something went wrong
            metadata: Optional metadata about the event
        """
        return ContentProcessingEvent(
            source_id=source_id,
            event_type=EventType.CONTENT_PROCESSING,  # This is fixed for content processing events
            stage=stage,  # The stage parameter maps to what was previously event_type
            error=error,
            metadata=metadata,
        )

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
