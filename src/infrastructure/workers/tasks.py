import time

from src.infrastructure.common.logger import get_logger

logger = get_logger()


def test_job(job_id: str):
    logger.info(f"Test job {job_id} started")
    time.sleep(5)  # Simulate some work
    logger.info(f"Test job {job_id} completed")
    return f"Job {job_id} completed"
