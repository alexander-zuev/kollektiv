# job_manager.py
from typing import Any
from uuid import UUID

from src.core._exceptions import JobNotFoundError
from src.infra.logger import get_logger
from src.models.job_models import (
    CrawlJobDetails,
    Job,
    JobType,
    ProcessingJobDetails,
)
from src.services.data_service import DataService

logger = get_logger()


class JobManager:
    """Manages job lifecycle and operations."""

    def __init__(self, data_service: DataService) -> None:
        self.data_service = data_service

    async def create_job(self, job_type: JobType, details: CrawlJobDetails | ProcessingJobDetails) -> Job:
        """
        Create and persist a new job.

        Args:
            job_type: Type of job to create
            details: Details to create

        Returns:
            Job: The created job instance
        """
        job = Job(job_type=job_type, details=details)
        return await self.data_service.save_job(job)

    async def update_job(self, job_id: UUID, updates: dict[str, Any]) -> Job:
        """
        Update a job with new data.

        Args:
            job_id: UUID of the job to update
            updates: Dictionary of updates to apply

        Returns:
            Job: Updated job instance

        Raises:
            JobNotFoundError: If job with given ID doesn't exist
        """
        # Get current job state
        job = await self.data_service.get_job(job_id)
        if not job:
            raise JobNotFoundError(f"Job {job_id} not found")

        # Apply updates
        updated_job = job.update(**updates)

        # Persist and return
        return await self.data_service.save_job(updated_job)

    async def get_by_firecrawl_id(self, firecrawl_id: str) -> Job:
        """
        Retrieve a job by its FireCrawl ID.

        Args:
            firecrawl_id: FireCrawl identifier

        Returns:
            Job: The requested job instance

        Raises:
            JobNotFoundError: If job with given FireCrawl ID doesn't exist
        """
        job = await self.data_service.get_by_firecrawl_id(firecrawl_id)
        if not job:
            raise JobNotFoundError(f"Job with FireCrawl ID {firecrawl_id} not found")
        return job

    async def mark_job_completed(self, job_id: UUID, result_id: UUID | None = None) -> Job:
        """Mark a job as completed."""
        # job = await self.get_job(job_id)
        job = await self.data_service.get_job(job_id)
        if not job:
            raise JobNotFoundError(f"Job {job_id} not found")
        job.complete()
        return await self.data_service.save_job(job)

    async def mark_job_failed(self, job_id: UUID, error: str) -> Job:
        """Mark a job as failed with error information."""
        # job = await self.get_job(job_id)
        job = await self.data_service.get_job(job_id)
        if not job:
            raise JobNotFoundError(f"Job {job_id} not found")
        job.fail(error)
        return await self.data_service.save_job(job)
