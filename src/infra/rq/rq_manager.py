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

    @classmethod
    def create(cls, redis_manager: RedisManager) -> "RQManager":
        """Create an instance of RQManager."""
        instance = cls(redis_manager)
        instance._connect_queue()
        return instance

    @tenacity_retry_wrapper(exceptions=(ConnectionError, TimeoutError))
    def _connect_queue(self) -> None:
        """Connect to a queue."""
        if self._queue is None:
            try:
                self._queue = Queue(
                    name=settings.redis_queue_name,
                    connection=self.redis_manager.get_sync_client(),
                    default_timeout=settings.processing_queue_timeout,
                )
                logger.info(f"Created queue {self._queue.name}")
            except (ConnectionError, TimeoutError) as e:
                logger.exception(f"Failed to create queue: {e}")
                raise

    def _get_queue(self) -> Queue:
        """Get a queue."""
        self._connect_queue()
        return self._queue

    # @property
    # def queue(self) -> Queue:
    #     """Get a syncchronious connection to RQ queue for processing jobs."""
    #     if self._queue is None:
    #         self._queue = Queue(
    #             name=settings.redis_queue_name,
    #             connection=self.redis_manager.get_sync_client(),
    #             default_timeout=settings.processing_queue_timeout,
    #         )
    #     return self._queue

    @tenacity_retry_wrapper(exceptions=(ConnectionError, TimeoutError))
    def enqueue_job(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> job.Job:  # type: ignore
        """Enqueue a job to the specified queue."""
        try:
            queue = self._get_queue()
            result = queue.enqueue(func, *args, **kwargs)
            logger.debug(f"Successfully enqueued job {result.id}")
            return result
        except (ConnectionError, TimeoutError) as e:
            logger.exception(f"Failed to enqueue job: {e}")
            raise
