# job_manager.py
from uuid import UUID

from src.infrastructure.common.decorators import base_error_handler
from src.infrastructure.config.logger import get_logger
from src.models.common.jobs import CrawlJob
from src.services.data_service import DataService

logger = get_logger()


class JobManager:
    """Manages crawl job lifecycle and operations.

    This class handles the creation, retrieval, and updating of crawl jobs,
    delegating persistence operations to the DataService.

    Args:
        data_service (DataService): Service for handling data persistence
    """

    def __init__(self, data_service: DataService):
        """Initialize JobManager with data service."""
        self.data_service = data_service
        logger.debug("Initialized JobManager")

    @base_error_handler
    async def create_job(self, source_id: UUID, start_url: str) -> CrawlJob:
        """Create and persist a new job.

        Args:
            source_id: ID of the associated source
            start_url: URL to start crawling from

        Returns:
            CrawlJob: The created job
        """
        job = CrawlJob(source_id=source_id, start_url=start_url)
        await self.data_service.save_job(job=job)
        logger.debug(f"Created job {job.job_id} for source {source_id}")
        return job

    @base_error_handler
    async def get_job(self, job_id: UUID) -> CrawlJob:
        """Get job by ID.

        Args:
            job_id: ID of the job to retrieve

        Returns:
            CrawlJob: The retrieved job

        Raises:
            JobNotFoundError: If job doesn't exist
        """
        return await self.data_service.retrieve_job(job_id=job_id)

    @base_error_handler
    async def update_job(self, job: CrawlJob) -> None:
        """Update existing job.

        Args:
            job: Job with updated data
        """
        await self.data_service.update_job(job=job)
        logger.debug(f"Updated job {job.job_id}")

    @base_error_handler
    async def get_job_by_firecrawl_id(self, firecrawl_id: str) -> CrawlJob:
        """Get job by FireCrawl ID.

        Args:
            firecrawl_id: FireCrawl job identifier

        Returns:
            CrawlJob: The retrieved job

        Raises:
            JobNotFoundError: If no job exists with the FireCrawl ID
        """
        return await self.data_service.get_job_by_firecrawl_id(firecrawl_id=firecrawl_id)

    @base_error_handler
    async def list_jobs(self, source_id: UUID | None = None) -> list[CrawlJob]:
        """List all jobs, optionally filtered by source.

        Args:
            source_id: Optional source ID to filter jobs

        Returns:
            list[CrawlJob]: List of matching jobs
        """
        return await self.data_service.list_jobs(source_id=source_id)
