from collections.abc import Callable
from typing import Any

from redis.exceptions import ConnectionError, TimeoutError
from rq import Queue, job

from src.infra.decorators import tenacity_retry_wrapper
from src.infra.external.redis_manager import RedisManager
from src.infra.logger import get_logger
from src.infra.settings import settings

logger = get_logger()


class RQManager:
    """Manages RQ queues."""

    def __init__(self, redis_manager: RedisManager) -> None:
        """Initialize RQManager with a synchronous Redis connection."""
        self.redis_manager = redis_manager
        self._queue: Queue | None = None

    @property
    def queue(self) -> Queue:
        """Get a syncchronious connection to RQ queue for processing jobs."""
        if self._queue is None:
            self._queue = Queue(
                name=settings.redis_queue_name,
                connection=self.redis_manager.get_sync_client(),
                default_timeout=settings.processing_queue_timeout,
            )
        return self._queue

    @tenacity_retry_wrapper(exceptions=(ConnectionError, TimeoutError))
    def enqueue_job(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> job.Job:  # type: ignore
        """Enqueue a job to the specified queue."""
        try:
            return self.queue.enqueue(func, *args, **kwargs)
        except (ConnectionError, TimeoutError) as e:
            logger.exception(f"Failed to enqueue job: {e}")
            raise
