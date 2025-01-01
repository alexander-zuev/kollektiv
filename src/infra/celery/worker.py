import asyncio
from typing import Any

from celery import Celery
from celery.signals import worker_init

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


def run_worker() -> None:
    """Run the Celery worker programmatically."""

    @worker_init.connect
    def on_worker_init(sender: Any, **kwargs: Any) -> None:
        """Initialize the worker services."""
        try:
            worker_services = asyncio.run(WorkerServices.create())
            celery_app.services = worker_services
        except Exception as e:
            logger.exception(f"Failed to initialize worker services: {e}")

    if settings.environment in (Environment.LOCAL, Environment.STAGING):
        celery_app.start(argv=["worker", "--loglevel=debug"])
    else:
        celery_app.start(argv=["worker", "--loglevel=info"])
