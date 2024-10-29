from datetime import datetime, timezone

from src.crawling.exceptions import InvalidWebhookEventError, JobNotFoundException
from src.crawling.job_manager import JobManager
from src.crawling.models import CrawlJob, CrawlJobStatus, WebhookEvent, WebhookEventType
from src.utils.decorators import base_error_handler
from src.utils.logger import get_logger

logger = get_logger()


class WebhookHandler:
    """Handles webhook events and coordinates job updates"""

    def __init__(self, job_manager: JobManager):
        self.job_manager = job_manager

    @base_error_handler
    async def handle_event(self, event: WebhookEvent) -> None:
        """Handle webhook events from Firecrawl"""
        try:
            logger.info(f"Received webhook event: {event.type} for FireCrawl job {event.id}")
            logger.debug(f"Event data: {event.model_dump()}")

            # Get job by FireCrawl ID
            job = await self.job_manager.get_job_by_firecrawl_id(event.id)

            if not event.success:
                logger.error(f"Event failed: {event.error}")
                await self._handle_failure(job, event.error or "Unknown error")
                return

            match event.type:
                case WebhookEventType.STARTED:
                    logger.info(f"Crawl started for job {job.id}")
                    await self._handle_started(job)

                case WebhookEventType.PAGE:
                    logger.info(f"Page crawled for job {job.id}")
                    await self._handle_page_crawled(job)

                case WebhookEventType.COMPLETED:
                    logger.info(f"Crawl completed for job {job.id}")
                    await self._handle_completed(job)

                case WebhookEventType.FAILED:
                    logger.error(f"Crawl failed for job {job.id}: {event.error}")
                    await self._handle_failure(job, event.error or "Unknown error")

        except JobNotFoundException as e:
            logger.error(f"Job not found: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unhandled error in webhook handler: {str(e)}", exc_info=True)
            if "job" in locals():
                await self._handle_failure(job, f"Internal error: {str(e)}")
            raise

    @base_error_handler
    async def _handle_started(self, job: CrawlJob) -> None:
        """Handle crawl.started event"""
        job.status = CrawlJobStatus.IN_PROGRESS
        job.started_at = datetime.now(timezone.utc)
        await self.job_manager.update_job(job)

    @base_error_handler
    async def _handle_page_crawled(self, job: CrawlJob) -> None:
        """Handle crawl.page event - increment page count"""
        job.pages_crawled += 1
        logger.debug(f"Pages crawled: {job.pages_crawled}")
        await self.job_manager.update_job(job)

    @base_error_handler
    async def _handle_completed(self, job: CrawlJob) -> None:
        """Handle crawl.completed event"""
        job.status = CrawlJobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        job.total_pages = job.pages_crawled  # Set total pages to what we've crawled
        job.progress_percentage = 100.0
        await self.job_manager.update_job(job)

    @base_error_handler
    async def _handle_failure(self, job: CrawlJob, error: str) -> None:
        """Handle crawl.failed event"""
        job.status = CrawlJobStatus.FAILED
        job.error = error
        job.completed_at = datetime.now(timezone.utc)
        await self.job_manager.update_job(job)
