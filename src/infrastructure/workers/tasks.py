import time

from src.infrastructure.common.logger import get_logger

logger = get_logger()


def test_job(job_id: str):
    """A test job to simulate some work."""
    logger.info(f"Test job {job_id} started")
    time.sleep(5)  # Simulate some work
    logger.info(f"Test job {job_id} completed")
    return f"Job {job_id} completed"


def chat_service_job(job_id: str) -> str:
    """Simulates a chat service job."""
    logger.info(f"Executing chat service job with ID: {job_id}")
    return f"Chat job {job_id} completed"


def crawler_service_job(job_id: str) -> str:
    """Simulates a crawler service job."""
    logger.info(f"Executing crawler service job with ID: {job_id}")
    return f"Crawler job {job_id} completed"
