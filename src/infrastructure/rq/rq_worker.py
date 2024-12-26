from rq.worker import Worker

from src.infrastructure.common.logger import configure_logging, get_logger
from src.infrastructure.config.settings import settings
from src.infrastructure.external.redis_client import RedisClient
from src.infrastructure.rq.worker_services import WorkerServices

configure_logging(debug=True)
logger = get_logger()

logger.info("Starting RQ worker")

services = WorkerServices.get_instance()


# Start worker
def start_worker() -> None:
    """Start worker with retry logic."""
    redis_client = RedisClient().sync_client
    worker = Worker([settings.redis_queue_name], connection=redis_client)
    logger.info(f"Starting worker on queue: {settings.redis_queue_name}")
    worker.work()


if __name__ == "__main__":
    start_worker()
