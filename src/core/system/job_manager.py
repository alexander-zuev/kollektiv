# job_manager.py
import json
from pathlib import Path

import aiofiles

from src.core._exceptions import JobNotFoundError
from src.infrastructure.common.decorators import base_error_handler
from src.infrastructure.config.logger import get_logger
from src.models.common.jobs import CrawlJob, CrawlJobStatus

logger = get_logger()


class JobManager:
    """Manages crawl job lifecycle and storage.

    This class handles the creation, retrieval, and updating of crawl jobs,
    including their persistence to storage.

    Args:
        storage_dir (str): Directory path for storing job data.

    Attributes:
        storage_dir (Path): Path object for the storage directory.
        jobs_file (Path): Path object for the jobs JSON file.
    """

    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.jobs_file = self.storage_dir / "jobs.json"
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Ensure storage directory exists and initialize jobs file if needed."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        if not self.jobs_file.exists():
            self.jobs_file.write_text("{}")

    @base_error_handler
    async def create_job(self, firecrawl_id: str, start_url: str) -> CrawlJob:
        """Create new job."""
        job = CrawlJob(firecrawl_id=firecrawl_id, start_url=start_url, status=CrawlJobStatus.PENDING)
        await self._save_job(job)
        return job

    @base_error_handler
    async def get_job(self, job_id: str) -> CrawlJob:
        """Get job by ID."""
        jobs = await self._load_jobs()
        job_data = jobs.get(job_id)
        if not job_data:
            raise JobNotFoundError(job_id)
        return CrawlJob(**job_data)

    @base_error_handler
    async def update_job(self, job: CrawlJob) -> None:
        """Update job state."""
        await self._save_job(job)

    @base_error_handler
    async def _save_job(self, job: CrawlJob) -> None:
        """Save job with basic validation.

        Args:
            job (CrawlJob): The job to save.
        """
        jobs = await self._load_jobs()
        jobs[job.id] = job.model_dump(mode="json")
        async with aiofiles.open(self.jobs_file, "w") as f:
            await f.write(json.dumps(jobs, indent=2))
        logger.debug(f"Saved job {job.id} with status {job.status}")

    @base_error_handler
    async def _load_jobs(self) -> dict:
        """Load jobs from storage.

        Returns:
            dict: Dictionary of jobs keyed by job ID.
        """
        try:
            async with aiofiles.open(self.jobs_file) as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Error loading jobs: {e}")
            return {}

    @base_error_handler
    async def get_job_by_firecrawl_id(self, firecrawl_id: str) -> CrawlJob:
        """Get job by FireCrawl ID."""
        jobs = await self._load_jobs()
        for job_data in jobs.values():
            if job_data["firecrawl_id"] == firecrawl_id:
                return CrawlJob(**job_data)
        raise JobNotFoundError(f"No job found for FireCrawl ID: {firecrawl_id}")
