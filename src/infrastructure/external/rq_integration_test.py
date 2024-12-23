import asyncio
import logging
from uuid import uuid4

from rq.job import JobStatus

from src.infrastructure.common.logger import get_logger
from src.infrastructure.external.redis_client import RedisClient
from src.infrastructure.workers.tasks import test_job

logger = get_logger()


async def test_rq_integration() -> None:
    """Test RQ integration."""
    try:
        redis_client = RedisClient()
        queue = redis_client.get_queue()

        # Enqueue a test job
        job_id = str(uuid4())
        job = queue.enqueue(test_job, args=[job_id])
        logger.info(f"Test job enqueued with ID: {job.id}")

        # Wait for job to complete
        while not job.is_finished:
            logger.info(f"Waiting for job {job.id} to complete...")
            await asyncio.sleep(1)

        # Get final status and result
        final_status = job.get_status()

        if final_status == JobStatus.FINISHED:
            result = job.result
            logger.info(f"Job {job.id} completed successfully with result: {result}")
        elif final_status == JobStatus.FAILED:
            logger.error(f"Job {job.id} failed with exception: {job.exc_info}")
        else:
            logger.warning(f"Job {job.id} has unknown status: {final_status}")

    except Exception as e:
        logger.error(f"RQ integration test failed: {str(e)}")
        raise


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    asyncio.run(test_rq_integration())
