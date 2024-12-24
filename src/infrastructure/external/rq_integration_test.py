import asyncio
import logging
from uuid import uuid4

from rq.job import Job, JobStatus

from src.infrastructure.common.logger import get_logger
from src.infrastructure.external.redis_client import RedisClient
from src.infrastructure.workers.tasks import chat_servibce_job, crawler_service_job

logger = get_logger()


async def test_rq_integration() -> None:
    """Test RQ integration with multiple services on the same queue."""
    try:
        redis_client = RedisClient()

        # Get the default queue
        queue = redis_client.get_queue()

        # Enqueue jobs
        jobs: list[Job] = []
        n_chat_jobs = 5
        n_crawler_jobs = 5

        for i in range(n_chat_jobs):
            job_id = str(uuid4())
            job = queue.enqueue(chat_service_job, args=[job_id])
            logger.info(f"Chat job enqueued with ID: {job.id}")
            jobs.append(job)

        for i in range(n_crawler_jobs):
            job_id = str(uuid4())
            job = queue.enqueue(crawler_service_job, args=[job_id])
            logger.info(f"Crawler job enqueued with ID: {job.id}")
            jobs.append(job)

        # Wait for all jobs to complete
        while any(not job.is_finished for job in jobs):
            logger.info("Waiting for jobs to complete...")
            await asyncio.sleep(1)

        # Verify job status and results
        job_results: dict[str, str] = {}
        for job in jobs:
            final_status = job.get_status()
            if final_status == JobStatus.FINISHED:
                result = job.result
                logger.info(f"Job {job.id} completed successfully with result: {result}")
                job_results[job.id] = result
            elif final_status == JobStatus.FAILED:
                logger.error(f"Job {job.id} failed with exception: {job.exc_info}")
            else:
                logger.warning(f"Job {job.id} has unknown status: {final_status}")

        # Verify that all jobs completed successfully
        if len(job_results) != len(jobs):
            raise Exception("Not all jobs completed successfully")

        logger.info("All jobs completed successfully!")

    except Exception as e:
        logger.error(f"RQ integration test failed: {str(e)}")
        raise


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    asyncio.run(test_rq_integration())
