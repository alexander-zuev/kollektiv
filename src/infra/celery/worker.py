import asyncio
import os
from typing import Any

from celery import Celery
from celery.signals import worker_process_init

from src.infra.celery.worker_services import WorkerServices
from src.infra.logger import configure_logging, get_logger
from src.infra.settings import get_settings
from src.models.base_models import Environment

# Initialize logging
configure_logging()
logger = get_logger()

# Get settings using the getter
settings = get_settings()

celery_app = Celery(
    "kollektiv-worker",
    broker=settings.broker_url,
    backend=settings.result_backend,
)
# Tell Celery to look for tasks in these modules
celery_app.autodiscover_tasks(["src.infra.celery"])


@worker_process_init.connect
def init_worker_process(*args: Any, **kwargs: Any) -> None:
    """Initialize worker services for each worker process."""
    try:
        process_id = os.getpid()
        logger.info(f"[Worker Process {process_id}] Starting service initialization")

        worker_services = asyncio.run(WorkerServices.create())
        celery_app.services = worker_services
        logger.info(f"[Worker Process {process_id}] ✓ Successfully initialized services")
    except Exception as e:
        logger.exception(f"Failed to initialize worker services: {e}")
        raise


def run_worker() -> None:
    """Run the Celery worker programmatically."""
    if settings.environment in (Environment.LOCAL, Environment.STAGING):
        celery_app.start(argv=["worker", "--loglevel=debug", f"--concurrency={settings.worker_concurrency}"])
    else:
        celery_app.start(argv=["worker", "--loglevel=info", f"--concurrency={settings.worker_concurrency}"])
