import asyncio
import json
from uuid import UUID

import redis
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.infra.external.redis_client import AsyncRedis
from src.infra.logger import get_logger
from src.infra.settings import settings
from src.models.job_models import JobStatus
from src.services.content_service import ContentService

logger = get_logger()


class EventService:
    """Handles events from the event bus."""

    def __init__(self, redis_client: AsyncRedis, content_service: ContentService) -> None:
        self.redis_client = redis_client
        self.content_service = content_service
        self.pubsub = redis_client.pubsub()

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        before_sleep=lambda retry_state: logger.warning(
            f"Redis connection attempt {retry_state.attempt_number} failed, retrying..."
        ),
    )
    async def start(self) -> None:
        """Start listening for events from the event bus."""
        try:
            await self.pubsub.subscribe(settings.process_documents_channel)
            asyncio.create_task(self.listen_for_events())
        except Exception as e:
            logger.error(f"Failed to subscribe to channel {settings.process_documents_channel}: {e}")
            raise

    async def listen_for_events(self) -> None:
        """Listen for events from the event bus."""
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    await self.handle_event(message["data"])
        except redis.exceptions.ConnectionError as e:
            logger.exception(f"Failed to listen for events: {e}")
            raise

    async def publish_event(self, event: dict, queue: str = settings.process_documents_channel) -> None:
        """Publish an event to the event bus."""
        await self.redis_client.publish(queue, json.dumps(event))

    async def handle_event(self, message: bytes) -> None:
        """Handle an event from the event bus."""
        try:
            event_data = json.loads(message.decode("utf-8"))
            job_id = UUID(event_data["job_id"])
            status = JobStatus(event_data["status"])

            await self.content_service.handle_job_event(job_id=job_id, status=status, error=event_data.get("error"))
        except Exception as e:
            logger.error(f"Failed to handle event: {e}")
            raise

    async def stop(self) -> None:
        """Stop listening for events from the event bus."""
        await self.pubsub.unsubscribe()
        await self.pubsub.aclose()
