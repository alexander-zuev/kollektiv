from collections.abc import Callable
from typing import Any

from redis import Redis
from rq import Queue, job

from src.infra.logger import get_logger
from src.infra.settings import settings

logger = get_logger()


class RQManager:
    """Manages RQ queues."""

    def __init__(self, redis_client: Redis) -> None:
        """Initialize RQManager with a Redis connection."""
        self.redis_client = redis_client
        self.queue = Queue(
            name=settings.redis_queue_name,
            connection=self.redis_client,
            default_timeout=settings.processing_queue_timeout,
        )
        logger.info("✓ Initialized RQManager successfully")
        logger.debug(f"Queue: {self.queue}")

    def get_queue(self) -> Queue:
        """Get the RQ queue for processing jobs."""
        return self.queue

    def enqueue_job(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> job.Job:  # type: ignore
        """Enqueue a job to the specified queue."""
        return self.queue.enqueue(func, *args, **kwargs)
