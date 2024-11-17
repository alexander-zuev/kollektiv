# job_manager.py
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.core._exceptions import JobNotFoundError, ValidationError
from src.infrastructure.common.decorators import generic_error_handler
from src.infrastructure.config.logger import get_logger
from src.models.common.job_models import (
    CrawlJobDetails,
    Job,
    JobStatus,
    JobType,
)
from src.services.data_service import DataService

logger = get_logger()


class JobManager:
    """Manages job lifecycle and operations."""

    def __init__(self, data_service: DataService) -> None:
        self.data_service = data_service

    def _create_job_details(self, job_type: JobType, **kwargs: Any) -> dict:
        """
        Create job details based on job type.

        Args:
            job_type: Type of job to create
            **kwargs: Parameters specific to job type:
                     - For CRAWL jobs:
                       - source_id (UUID): ID of the source to crawl.

        Returns:
            dict: Validated job details

        Raises:
            ValidationError: If unsupported job type
        """
        match job_type:
            case JobType.CRAWL:
                return CrawlJobDetails(**kwargs).model_dump()
            case _:
                raise ValidationError(f"Unsupported job type: {job_type}")

    @generic_error_handler
    async def create_job(self, job_type: JobType, **kwargs: Any) -> Job:
        """
        Create and persist a new job.

        Args:
            job_type: Type of job to create
            **kwargs: Optional parameters specific to job type:
                     - For CRAWL jobs:
                       - source_id (UUID): ID of the source to crawl.

        Returns:
            Job: The created job instance

        Example:
            job = await job_manager.create_job(
                job_type=JobType.CRAWL,
                source_id=existing_uuid
            )
        """
        details = self._create_job_details(job_type, **kwargs)
        job = Job(job_type=job_type, details=details)
        return await self.data_service.save_job(job)

    @generic_error_handler
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
        job = await self.get_job(job_id)
        if not job:
            raise JobNotFoundError(f"Job {job_id} not found")

        # Add updated_at
        updates["updated_at"] = datetime.now(UTC)

        # Apply updates
        updated_job = job.update(**updates)

        # Persist and return
        return await self.data_service.save_job(updated_job)

    @generic_error_handler
    async def get_job(self, job_id: UUID) -> Job:
        """
        Retrieve a job by ID.

        Args:
            job_id: UUID of the job to retrieve

        Returns:
            Job: The requested job instance

        Raises:
            JobNotFoundError: If job with given ID doesn't exist
        """
        job = await self.data_service.get_job(job_id)
        if not job:
            raise JobNotFoundError(f"Job {job_id} not found")
        return job

    @generic_error_handler
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
        """
        Mark a job as completed with optional result ID.

        Args:
            job_id: UUID of the job to complete
            result_id: Optional UUID of the result in storage

        Returns:
            Job: Updated job instance
        """
        return await self.update_job(
            job_id, {"status": JobStatus.COMPLETED, "completed_at": datetime.now(UTC), "result_id": result_id}
        )

    async def mark_job_failed(self, job_id: UUID, error: str) -> Job:
        """
        Mark a job as failed with error information.

        Args:
            job_id: UUID of the job to mark as failed
            error: Error message describing the failure

        Returns:
            Job: Updated job instance
        """
        return await self.update_job(
            job_id, {"status": JobStatus.FAILED, "completed_at": datetime.now(UTC), "error": error}
        )
