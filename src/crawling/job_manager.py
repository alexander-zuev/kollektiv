# job_manager.py
from pathlib import Path
import json
from typing import Optional

import aiofiles

from src.crawling.exceptions import JobNotFoundException
from src.crawling.models import CrawlJob, CrawlJobStatus, WebhookEvent, WebhookEventType
from src.utils.logger import get_logger

logger = get_logger()

class JobManager:
    """Manages crawl job lifecycle"""

    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.jobs_file = self.storage_dir / "jobs.json"
        self._ensure_storage()

    def _ensure_storage(self):
        """Ensure storage directory exists"""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        if not self.jobs_file.exists():
            self.jobs_file.write_text("{}")

    async def create_job(self, firecrawl_id: str, start_url: str) -> CrawlJob:
        """Create new job"""
        job = CrawlJob(
            firecrawl_id=firecrawl_id,
            start_url=start_url,
            status=CrawlJobStatus.PENDING
        )
        #TODO: Refactor to use FileManager
        await self._save_job(job)
        return job

    async def get_job(self, job_id: str) -> Optional[CrawlJob]:
        """Get job by ID"""
        #TODO: refacotor to use FileManager
        jobs = await self._load_jobs()
        job_data = jobs.get(job_id)
        return CrawlJob(**job_data) if job_data else None

    async def update_job(self, job: CrawlJob) -> None:
        """Update job state"""
        await self._save_job(job)

    async def _save_job(self, job: CrawlJob) -> None:
        """Save job with proper async IO"""
        jobs = await self._load_jobs()
        job_data = job.model_dump(mode='json')
        jobs[job.id] = job_data
        async with aiofiles.open(self.jobs_file, 'w') as f:
            await f.write(json.dumps(jobs, indent=2))


    #TODO: refactor to use FileManager
    async def _load_jobs(self) -> dict:
        """Load jobs from storage"""
        try:
            json_data = self.jobs_file.read_text()
            return json.loads(json_data)
        except Exception as e:
            return {}


    async def start_job(self, job_id: str):
        """Update job status to IN_PROGRESS when the job starts."""
        job = await self.get_job(job_id)
        job.status = CrawlJobStatus.IN_PROGRESS
        await self.update_job(job)

    async def update_job_progress(self, job_id: str, progress_percentage: float):
        """Update job progress while it is in progress."""
        job = await self.get_job(job_id)
        job.status = CrawlJobStatus.IN_PROGRESS
        job.progress_percentage = progress_percentage
        await self.update_job(job)

    async def complete_job(self, job_id: str, result_data):
        """Complete the job and save final results."""
        job = await self.get_job(job_id)
        job.status = CrawlJobStatus.COMPLETED
        job.result_data = result_data
        await self.update_job(job)

    async def fail_job(self, job_id: str, error_message: str):
        """Fail the job and log an error message."""
        job = await self.get_job(job_id)
        job.status = CrawlJobStatus.FAILED
        job.error = error_message
        await self.update_job(job)

    # TODO: consider if this belongs here? Why JobManage handles events?
    async def handle_webhook_event(self, event: WebhookEvent) -> CrawlJob:
        """Handle webhook with validation"""
        if not event.success:
            logger.error(f"Webhook event failed: {event.error}")

        job = await self.get_job(event.jobId)
        if not job:
            raise JobNotFoundException(f"Job {event.jobId} not found")

        match event.type:
            case WebhookEventType.STARTED:
                job.mark_started()

            case WebhookEventType.PAGE_CRAWLED:
                job.update_progress(event.completed, event.total)

            case WebhookEventType.COMPLETED:
                job.mark_completed(None)  # Result file set later

            case WebhookEventType.FAILED:
                job.mark_failed(event.error)

        await self.update_job(job)
        return job