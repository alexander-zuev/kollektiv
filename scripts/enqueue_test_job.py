from redis import Redis
from rq import job

from src.infra.rq.rq_manager import RQManager
from src.infra.rq.tasks import test_services_connectivity


def enqueue_test_job() -> list[job.Job]:
    # Use same Redis URL as workers
    redis_url = "redis://localhost:6379/0"  # Maps to container through port mapping
    redis_client = Redis.from_url(redis_url)

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
