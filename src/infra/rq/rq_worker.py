from rq.worker import Worker

from src.infra.external.redis_client import RedisClient
from src.infra.logger import configure_logging, get_logger
from src.infra.rq.worker_services import WorkerServices
from src.infra.settings import settings

# Configure logging
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
