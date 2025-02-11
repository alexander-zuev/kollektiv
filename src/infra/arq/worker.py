from concurrent import futures
from typing import Any

from src.infra.arq.arq_settings import get_arq_settings
from src.infra.arq.serializer import deserialize, serialize
from src.infra.arq.task_definitions import task_list
from src.infra.arq.worker_services import WorkerServices
from src.infra.logger import configure_logging, get_logger
from src.infra.settings import get_settings

settings = get_settings()
arq_settings = get_arq_settings()

configure_logging()
logger = get_logger()


async def on_startup(ctx: dict[str, Any]) -> None:
    """Runs on startup."""
    ctx["worker_services"] = await WorkerServices.create()
    ctx["arq_redis"] = ctx["worker_services"].arq_redis_pool
    ctx["pool"] = futures.ProcessPoolExecutor()


async def on_shutdown(ctx: dict[str, Any]) -> None:
    """Runs on shutdown."""
    await ctx["worker_services"].shutdown_services()


class WorkerSettings:
    """Settings for the Arq worker."""

    functions = task_list
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings = arq_settings.redis_settings
    health_check_interval = arq_settings.health_check_interval
    max_jobs = arq_settings.max_jobs
    max_retries = arq_settings.job_retries
    job_serializer = serialize
    job_deserializer = deserialize
    keep_result = 60  # Keep results for 60 seconds after completion


def run_worker() -> None:
    """Run Arq worker."""
    import sys

    from arq.cli import cli

    sys.argv = ["arq", "src.infra.arq.worker.WorkerSettings"]
    cli()
