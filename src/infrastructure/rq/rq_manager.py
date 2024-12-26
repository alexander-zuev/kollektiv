from collections.abc import Callable

from redis import Redis
from rq import Queue, job

from src.infrastructure.common.logger import get_logger
from src.infrastructure.config.settings import settings

logger = get_logger()


class RQManager:
    """Manages RQ queues."""

    def __init__(self, redis_client: Redis):
        """Initialize RQManager with a Redis connection."""
        self.redis_client = redis_client
        self.queue = Queue(
            name=settings.redis_queue_name,
            connection=self.redis_client,
            default_timeout=settings.processing_queue_timeout,
        )
        logger.info(f"Initialized RQManager with queue: {self.queue}")

    def get_queue(self) -> Queue:
        """Get the RQ queue for processing jobs."""
        return self.queue

    def enqueue(self, func: Callable, *args, **kwargs) -> job.Job:
        """Enqueue a job to the specified queue."""
        return self.queue.enqueue(func, *args, **kwargs)
