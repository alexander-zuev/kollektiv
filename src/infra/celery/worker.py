import asyncio

from celery import Celery

from src.infra.celery.worker_services import WorkerServices
from src.infra.logger import configure_logging, get_logger
from src.infra.settings import settings

configure_logging()
logger = get_logger()

celery_app = Celery(
    "kollektiv-worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Tell Celery to look for tasks in these modules
celery_app.autodiscover_tasks(["src.infra.celery"])


worker_services = asyncio.run(WorkerServices.create())
