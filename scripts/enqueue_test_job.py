from redis import Redis
from rq import job

from src.infrastructure.config.settings import settings
from src.infrastructure.rq.rq_manager import RQManager
from src.infrastructure.rq.tasks import test_services_connectivity


def enqueue_test_job() -> list[job.Job]:
    # Create Redis connection
    redis_client = Redis.from_url(settings.redis_url)

    # Initialize RQ manager
    rq_manager = RQManager(redis_client)

    # Enqueue multiple test jobs
    n_jobs = 3
    jobs = []

    for i in range(n_jobs):
        job = rq_manager.enqueue(test_services_connectivity, job_id=f"connectivity-test-{i}")
        print(f"Enqueued connectivity test job with ID: {job.id}")
        jobs.append(job)

    return jobs


if __name__ == "__main__":
    enqueue_test_job()
