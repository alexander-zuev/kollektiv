import asyncio

from rq.worker import Worker

from src.infra.logger import configure_logging, get_logger
from src.infra.rq.worker_services import WorkerServices
from src.infra.settings import settings


# Customer worker entrypoint
def start_worker() -> None:
    """Start worker with retry logic."""
    # Configure logging
    configure_logging(debug=True)
    logger = get_logger()
    logger.debug("Starting RQ worker")

    # Setup worker services
    worker_services = asyncio.run(WorkerServices.create())  # this sets up _instance

    redis_client = worker_services.sync_redis_manager.get_sync_client()
    worker = Worker([settings.redis_queue_name], connection=redis_client)
    logger.info(f"Started worker on queue: {settings.redis_queue_name}")
    worker.work()


if __name__ == "__main__":
    start_worker()
