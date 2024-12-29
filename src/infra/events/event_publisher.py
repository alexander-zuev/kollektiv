import json

from redis.exceptions import ConnectionError, TimeoutError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.infra.external.redis_client import AsyncRedis
from src.infra.logger import get_logger
from src.infra.settings import settings

logger = get_logger()


class EventPublisher:
    """Responsible for publishing events to the event bus."""

    def __init__(self, redis_client: AsyncRedis) -> None:
        self.redis_client = redis_client
        self.pubsub = redis_client.pubsub()

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        before_sleep=lambda retry_state: logger.warning(
            f"Redis connection attempt {retry_state.attempt_number} failed, retrying..."
        ),
    )
    async def publish_event(self, event: dict, queue: str = settings.process_documents_channel) -> None:
        """Publish an event to the event bus."""
        try:
            await self.pubsub.publish(queue, json.dumps(event))
            logger.info(f"Event published to {queue}: {event}")
        except ConnectionError as e:
            logger.exception(f"Failed to publish event to {queue}: {e}")
            raise
